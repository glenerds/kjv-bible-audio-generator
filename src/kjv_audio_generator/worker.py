from __future__ import annotations

import threading
import time
import hashlib
import json
from pathlib import Path
from typing import Callable

from .attribution import AttributionMap
from .audio import ChapterAudioAssembler
from .backend import SpeechBackend
from .models import BibleDocument, Chapter
from .storage import QueueStore, document_sha256
from .voices import VoiceRegistry


EventCallback = Callable[[str, dict], None]


class ChapterWorker:
    def __init__(self, document: BibleDocument, output_root: str | Path, registry: VoiceRegistry,
                 attribution: AttributionMap, backend: SpeechBackend, assembler: ChapterAudioAssembler,
                 max_attempts: int = 2, callback: EventCallback | None = None) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self.document = document
        self.output_root = Path(output_root)
        self.registry = registry
        self.attribution = attribution
        self.backend = backend
        self.assembler = assembler
        self.max_attempts = max_attempts
        self.callback = callback or (lambda _event, _data: None)
        self.store = QueueStore(self.output_root / "metadata" / "generation.sqlite3", output_root=self.output_root)
        self._chapter_segments: dict[tuple[str, int], list] = {}
        self._pause = threading.Event(); self._pause.set()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._error: BaseException | None = None

    def _emit(self, event: str, **data: object) -> None:
        self.callback(event, data)

    def _build_chapter_input_hashes(self, chapters: list[Chapter] | None = None) -> dict[tuple[str, int], str]:
        """Fingerprint every effective input that can change a chapter's audio.

        Kept as a deterministic helper so migrations and targeted invalidation can
        be tested without synthesizing a chapter first.
        """
        chapters = chapters if chapters is not None else self.document.ordered_chapters()
        self._chapter_segments = {}
        chapter_hashes: dict[tuple[str, int], str] = {}
        profile_hashes: dict[str, str] = {}
        settings = getattr(self.backend, "settings", None)
        backend_manifest_fingerprint = getattr(self.backend, "generation_fingerprint", None)
        backend_identity = {
            # Fingerprint the backend family, not a temporary subclass used for
            # instrumentation/diagnostics. This must remain stable across restarts.
            "backend": getattr(self.backend, "fingerprint_name", type(self.backend).__name__),
            "backend_version": getattr(self.backend, "fingerprint_version", "1"),
            "model_asset_fingerprint": str(backend_manifest_fingerprint()) if callable(backend_manifest_fingerprint) else None,
            "language": getattr(settings, "language", None),
            "device": getattr(settings, "device", None),
            "voice_design_model": Path(getattr(settings, "voice_design_model", "")).name if settings else None,
            "base_model": Path(getattr(settings, "base_model", "")).name if settings else None,
        }
        audio_fingerprint = getattr(self.assembler, "generation_fingerprint", None)
        audio_identity = {
            "pipeline_fingerprint": str(audio_fingerprint()) if callable(audio_fingerprint) else None,
            "bitrate_kbps": self.assembler.bitrate_kbps,
            "target_sample_rate": self.assembler.target_sample_rate,
            "gap_samples": self.assembler.gap_samples,
        }
        for chapter in chapters:
            segments = [segment for verse in chapter.verses for segment in self.attribution.segments_for(verse)]
            self._chapter_segments[(chapter.book, chapter.number)] = segments
            segment_rows = []
            for segment in segments:
                if segment.speaker_id not in profile_hashes:
                    profile = self.registry.get(segment.speaker_id)
                    fingerprint = getattr(self.backend, "profile_fingerprint", None)
                    if callable(fingerprint):
                        profile_hashes[segment.speaker_id] = str(fingerprint(profile))
                    else:
                        profile_hashes[segment.speaker_id] = hashlib.sha256(json.dumps({
                            "speaker_id": profile.speaker_id,
                            "voice_description": profile.voice_description,
                            "reference_text": profile.reference_text,
                            "reference_audio": profile.reference_audio,
                        }, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
                segment_rows.append({
                    "ref": segment.ref.label(),
                    "index": segment.index,
                    "speaker_id": segment.speaker_id,
                    "text": segment.text,
                    "profile_sha256": profile_hashes[segment.speaker_id],
                })
            payload = {
                "book": chapter.book,
                "chapter": chapter.number,
                "segments": segment_rows,
                "backend": backend_identity,
                "audio": audio_identity,
            }
            chapter_hashes[(chapter.book, chapter.number)] = hashlib.sha256(
                json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()
        return chapter_hashes

    def start(self, *, background: bool = True) -> None:
        if self._thread and self._thread.is_alive():
            raise RuntimeError("Generation is already running")
        chapters = self.document.ordered_chapters()
        chapter_hashes = self._build_chapter_input_hashes(chapters)
        invalidated = self.store.seed(chapters, document_sha256(chapters), chapter_hashes)
        if invalidated:
            self._emit("chapter_inputs_changed", count=invalidated)
        requeued = self.store.reconcile_completed_outputs()
        if requeued:
            self._emit("outputs_requeued", count=requeued)
        self._stop.clear(); self._pause.set(); self._error = None
        if background:
            self._thread = threading.Thread(target=self.run, name="KJVChapterGenerator", daemon=True)
            self._thread.start()
        else:
            self.run()

    def pause(self) -> None:
        self._pause.clear(); self._emit("paused", counts=self.store.progress())

    def resume(self) -> None:
        self._pause.set(); self._emit("resumed", counts=self.store.progress())

    def stop(self) -> None:
        self._stop.set(); self._pause.set(); self._emit("stop_requested")

    def join(self, timeout: float | None = None) -> None:
        if self._thread:
            self._thread.join(timeout)

    def _check_control(self) -> None:
        self._pause.wait()
        if self._stop.is_set():
            raise InterruptedError("Generation stopped by user")

    def run(self) -> None:
        try:
            initial_counts = self.store.progress()
            if initial_counts["pending"] == 0:
                # A completed Bible should be a no-op on repeated launch: do not
                # load the 1.7B runtime just to discover there is no work to do.
                report = self.store.export_report(self.output_root / "metadata" / "generation_report.json")
                self._emit("finished", counts=report["counts"],
                           failed=[r for r in report["chapters"] if r["status"] == "failed"],
                           stopped=False)
                return
            # Only prepare voices required by chapters that are still pending.
            # A Bible can contain hundreds of characters; on resume, regenerating
            # prompts for speakers whose chapters are already complete wastes large
            # amounts of CPU time and can make an unrelated stale profile block work.
            pending_keys = {
                (row["book"], int(row["chapter"]))
                for row in self.store.rows()
                if row["status"] == "pending"
            }
            pending_chapters = [
                chapter for chapter in self.document.ordered_chapters()
                if (chapter.book, chapter.number) in pending_keys
            ]
            pending_segments = [
                segment
                for chapter in pending_chapters
                for segment in self._chapter_segments[(chapter.book, chapter.number)]
            ]
            needed_ids = sorted({segment.speaker_id for segment in pending_segments})
            profiles = [self.registry.get(speaker_id) for speaker_id in needed_ids]
            self._emit("preparing_voices", speaker_ids=needed_ids)
            try:
                self.backend.prepare_profiles(
                    profiles,
                    control_check=self._check_control,
                    progress_callback=lambda phase, index, total, speaker: self._emit(
                        "voice_profile_progress", phase=phase, index=index, total=total, speaker_id=speaker
                    ),
                )
            except InterruptedError:
                report = self.store.export_report(self.output_root / "metadata" / "generation_report.json")
                self._emit("finished", counts=report["counts"],
                           failed=[r for r in report["chapters"] if r["status"] == "failed"], stopped=True)
                return
            # Persist prepared profile paths/status in the project output.
            self.registry.save(self.output_root / "metadata" / "voice_registry.json")
            self.attribution.save(self.output_root / "metadata" / "speaker_assignments.json")
            while not self._stop.is_set():
                self._pause.wait()
                if self._stop.is_set():
                    break
                job = self.store.claim_next()
                if job is None:
                    break
                book, number = job["book"], int(job["chapter"])
                chapter = self.document.chapter(book, number)
                self._emit("chapter_started", book=book, chapter=number, counts=self.store.progress())
                try:
                    segments = self._chapter_segments[(book, number)]
                    waveforms = []
                    for index, segment in enumerate(segments, start=1):
                        self._pause.wait()
                        if self._stop.is_set():
                            raise InterruptedError("Generation stopped by user")
                        waveform = self.backend.synthesize(segment.text, self.registry.get(segment.speaker_id))
                        waveforms.append(waveform)
                        self._emit("segment_generated", book=book, chapter=number, segment=index, total_segments=len(segments))
                    output_path, cue_path = self.assembler.write_chapter(book, number, segments, waveforms)
                    self.store.complete(book, number, str(output_path), str(cue_path))
                    self._emit("chapter_complete", book=book, chapter=number, output=str(output_path), counts=self.store.progress())
                except InterruptedError:
                    # A chapter interrupted mid-generation is safely retried from the beginning.
                    self.store.requeue_interrupted(book, number, "Interrupted by user; safe to resume")
                    break
                except Exception as exc:
                    status = self.store.fail(book, number, f"{type(exc).__name__}: {exc}", self.max_attempts)
                    self._emit("chapter_error", book=book, chapter=number, error=str(exc), status=status, counts=self.store.progress())
                    continue
            report = self.store.export_report(self.output_root / "metadata" / "generation_report.json")
            self._emit("finished", counts=report["counts"], failed=[r for r in report["chapters"] if r["status"] == "failed"], stopped=self._stop.is_set())
        except BaseException as exc:
            self._error = exc
            self._emit("fatal_error", error=f"{type(exc).__name__}: {exc}")
            try:
                self.store.export_report(self.output_root / "metadata" / "generation_report.json")
            except Exception:
                pass

    @property
    def error(self) -> BaseException | None:
        return self._error
