from __future__ import annotations

import json
from pathlib import Path

from kjv_audio_generator.attribution import AttributionMap
from kjv_audio_generator.backend import SyntheticTestBackend
from kjv_audio_generator.books import BOOKS, TOTAL_CHAPTERS
from kjv_audio_generator.models import (
    BibleDocument,
    KJV_CHAPTER_VERSE_COUNTS,
    Verse,
    VerseRef,
)
from kjv_audio_generator.voices import VoiceRegistry
from kjv_audio_generator.worker import ChapterWorker


class FastTestOnlyAssembler:
    """Write structurally valid placeholder outputs without running FFmpeg."""

    bitrate_kbps = 96
    target_sample_rate = 24000
    gap_samples = 0

    def __init__(self, output_root: Path) -> None:
        self.output_root = Path(output_root)

    @staticmethod
    def generation_fingerprint() -> str:
        return "fast-test-only-assembler-v1"

    def write_chapter(self, book, chapter_number, segments, waveforms):
        output_dir = self.output_root / book
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = f"{book.replace(' ', '_')}_{int(chapter_number):03d}"
        mp3_path = output_dir / f"{stem}.mp3"
        cue_path = self.output_root / "metadata" / "verse_timestamps" / f"{stem}.json"
        cue_path.parent.mkdir(parents=True, exist_ok=True)

        cue_segments = []
        cursor = 0.0
        for segment, (samples, sample_rate) in zip(segments, waveforms, strict=True):
            duration = max(0.01, float(len(samples)) / float(sample_rate))
            end = cursor + duration
            cue_segments.append({
                "reference": segment.ref.label(),
                "segment": int(segment.index),
                "speaker_id": segment.speaker_id,
                "text": segment.text,
                "start_seconds": round(cursor, 6),
                "end_seconds": round(end, 6),
            })
            cursor = end

        # The storage layer checks file presence, size, hashes and cue structure.
        # This deliberately is not a decodable MP3 and must never be used as audio.
        mp3_path.write_bytes(b"TEST_ONLY_PLACEHOLDER_MP3" + (b"\0" * 600))
        cue_path.write_text(json.dumps({
            "schema_version": 1,
            "book": book,
            "chapter": int(chapter_number),
            "duration_seconds": round(cursor, 6),
            "segments": cue_segments,
        }, ensure_ascii=False), encoding="utf-8")
        return mp3_path, cue_path


def test_synthetic_worker_completes_all_1189_chapters_and_31102_verses(tmp_path):
    verses = []
    for book, chapter_total in BOOKS:
        for chapter_number in range(1, chapter_total + 1):
            verse_count = KJV_CHAPTER_VERSE_COUNTS[book][chapter_number - 1]
            for verse_number in range(1, verse_count + 1):
                verses.append(Verse(
                    VerseRef(book, chapter_number, verse_number),
                    "x",
                ))

    document = BibleDocument.from_verses(verses, "synthetic-full-bible-worker-test")
    validation = document.validate_complete()
    assert (validation["books"], validation["chapters"], validation["verses"]) == (66, 1189, 31102)
    assert validation["complete_verse_count"] is True

    registry = VoiceRegistry.defaults()
    backend = SyntheticTestBackend(sample_rate=24000)
    worker = ChapterWorker(
        document,
        tmp_path,
        registry,
        AttributionMap(registry),
        backend,
        FastTestOnlyAssembler(tmp_path),
    )
    worker.start(background=False)

    expected_counts = {"pending": 0, "running": 0, "complete": TOTAL_CHAPTERS, "failed": 0}
    assert worker.error is None
    assert worker.store.progress() == expected_counts

    report_path = tmp_path / "metadata" / "generation_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["counts"] == expected_counts
    assert len(report["chapters"]) == TOTAL_CHAPTERS
    assert (report["chapters"][0]["book"], report["chapters"][0]["chapter"]) == ("Genesis", 1)
    assert (report["chapters"][-1]["book"], report["chapters"][-1]["chapter"]) == ("Revelation", 22)

    mp3_files = list(tmp_path.glob("*/*.mp3"))
    cue_files = list((tmp_path / "metadata" / "verse_timestamps").glob("*.json"))
    assert len(mp3_files) == TOTAL_CHAPTERS
    assert len(cue_files) == TOTAL_CHAPTERS
    cue_segment_total = sum(
        len(json.loads(path.read_text(encoding="utf-8"))["segments"])
        for path in cue_files
    )
    assert cue_segment_total == 31102
    assert backend.is_test_backend is True
