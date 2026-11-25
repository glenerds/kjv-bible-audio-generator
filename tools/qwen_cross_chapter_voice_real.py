from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np

from kjv_audio_generator.attribution import AttributionMap
from kjv_audio_generator.audio import ChapterAudioAssembler
from kjv_audio_generator.backend import QwenSettings, QwenVoiceBackend
from kjv_audio_generator.parser import parse_path
from kjv_audio_generator.voices import VoiceProfile, VoiceRegistry
from kjv_audio_generator.worker import ChapterWorker


PINNED_MODELS = {
    "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign": {
        "revision": "5ecdb67327fd37bb2e042aab12ff7391903235d3",
        "model_sha256": "391e8db219f292c515297cdceeb43e4eae67cdde35fa57e79a6a8a532fca0522",
        "speech_tokenizer_sha256": "836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258",
    },
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base": {
        "revision": "fd4b254389122332181a7c3db7f27e918eec64e3",
        "model_sha256": "38fc7fc51c5e776e840414b6fd443962e9411b9654888fd7913e4da643cb857c",
        "speech_tokenizer_sha256": "836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258",
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_integrity_report(path: Path) -> list[dict[str, Any]]:
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read pinned Qwen integrity report: {exc}") from exc
    if not isinstance(rows, list) or len(rows) != 2:
        raise RuntimeError("Qwen integrity report must contain exactly two model records.")
    by_repo = {row.get("repo"): row for row in rows if isinstance(row, dict)}
    if set(by_repo) != set(PINNED_MODELS):
        raise RuntimeError("Qwen integrity report does not identify both approved model snapshots.")
    for repo, expected in PINNED_MODELS.items():
        for field, expected_value in expected.items():
            if by_repo[repo].get(field) != expected_value:
                raise RuntimeError(
                    f"Qwen integrity mismatch for {repo}/{field}: "
                    f"expected {expected_value}, got {by_repo[repo].get(field)!r}"
                )
    return rows


def decode_probe(ffmpeg: str, path: Path) -> dict[str, float | int]:
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(path),
        "-ac", "1", "-ar", "24000", "-f", "f32le", "pipe:1",
    ]
    result = subprocess.run(command, capture_output=True, timeout=180, check=False)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace")[-1600:]
        raise RuntimeError(f"FFmpeg could not decode {path.name}: {detail}")
    if len(result.stdout) < 4 or len(result.stdout) % 4:
        raise RuntimeError(f"FFmpeg returned an invalid PCM byte count for {path.name}.")
    samples = np.frombuffer(result.stdout, dtype="<f4")
    if samples.size == 0 or not np.isfinite(samples).all():
        raise RuntimeError(f"Decoded audio is empty or non-finite: {path.name}")
    peak = float(np.max(np.abs(samples)))
    rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))
    duration = float(samples.size) / 24000.0
    if peak < 0.005 or rms < 0.0005:
        raise RuntimeError(f"Decoded audio appears silent: {path.name}; peak={peak:.6f}, rms={rms:.6f}")
    if peak > 1.2:
        raise RuntimeError(f"Decoded audio appears clipped: {path.name}; peak={peak:.6f}")
    return {
        "decoded_sample_rate": 24000,
        "decoded_frames": int(samples.size),
        "decoded_duration_seconds": round(duration, 3),
        "decoded_peak": round(peak, 6),
        "decoded_rms": round(rms, 6),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify that the same real Qwen narrator prompt is reused across Genesis 1 and 2."
    )
    parser.add_argument("--models-root", type=Path, required=True)
    parser.add_argument("--integrity-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu",), default="cpu")
    parser.add_argument("--ffmpeg", type=str, default=None)
    args = parser.parse_args()

    for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE"):
        if os.environ.get(name) not in {"1", "true", "TRUE"}:
            raise RuntimeError(f"{name}=1 is required for local-only cross-chapter inference.")

    integrity_rows = verify_integrity_report(args.integrity_report)
    ffmpeg = args.ffmpeg or shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg was not found; cross-chapter MP3 validation cannot run.")

    project_root = Path(__file__).resolve().parents[1]
    source = project_root / "examples" / "genesis_cross_chapter_voice_test.txt"
    if not source.is_file():
        raise RuntimeError(f"Cross-chapter KJV fixture is missing: {source}")
    document = parse_path(source)
    chapters = document.ordered_chapters()
    if [(chapter.book, chapter.number) for chapter in chapters] != [("Genesis", 1), ("Genesis", 2)]:
        raise RuntimeError("Cross-chapter fixture must contain exactly Genesis 1 and Genesis 2.")
    if len(chapters[0].verses) != 1 or len(chapters[1].verses) != 1:
        raise RuntimeError("Cross-chapter fixture must contain exactly one reviewed test verse per chapter.")

    verse_one = chapters[0].verses[0]
    verse_adam = chapters[1].verses[0]
    expected_one = "In the beginning God created the heaven and the earth."
    expected_adam = (
        "And Adam said, This is now bone of my bones, and of my flesh; "
        "she shall be called Woman, because she was taken out of Man."
    )
    if verse_one.ref.label() != "Genesis 1:1" or verse_one.text != expected_one:
        raise RuntimeError("Genesis 1:1 cross-chapter fixture differs from the approved KJV text.")
    expected_adam = (
        "And Adam said, This is now bone of my bones, and flesh of my flesh: "
        "she shall be called Woman, because she was taken out of Man."
    )
    if verse_adam.ref.label() != "Genesis 2:23" or verse_adam.text != expected_adam:
        raise RuntimeError("Genesis 2:23 cross-chapter fixture differs from the approved KJV text.")

    # KJV prose does not consistently delimit dialogue with quotation marks. This
    # reviewed test split is required to preserve every source character.
    overrides = {
        "Genesis 2:23": [
            {"speaker_id": "narrator", "text": "And Adam said, "},
            {
                "speaker_id": "adam",
                "text": (
                    "This is now bone of my bones, and flesh of my flesh; "
                    "she shall be called Woman, because she was taken out of Man."
                ),
            },
        ],
    }
    if "".join(item["text"] for item in overrides["Genesis 2:23"]) != verse_adam.text:
        raise RuntimeError("Manual Genesis 2:23 split does not preserve exact KJV text.")

    registry = VoiceRegistry.defaults()
    registry.add(VoiceProfile(
        speaker_id="adam",
        display_name="Adam",
        aliases=["the first man"],
        voice_description=(
            "Adult male human voice, natural and warm, clear and articulate; "
            "grounded mid-range register, calm thoughtful delivery with a slight "
            "sense of wonder. Avoid theatrical projection or an exaggerated accent."
        ),
        reference_text=(
            "I am Adam. This is now bone of my bones, and flesh of my flesh. "
            "I speak plainly, thoughtfully, and with natural warmth."
        ),
    ))
    attribution = AttributionMap(registry, segment_overrides=overrides)

    models_root = args.models_root.resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    backend = QwenVoiceBackend(
        QwenSettings(
            voice_design_model=models_root / "Qwen3-TTS-12Hz-1.7B-VoiceDesign",
            base_model=models_root / "Qwen3-TTS-12Hz-1.7B-Base",
            device=args.device,
            language="English",
        ),
        args.output_dir / "metadata" / "voice_assets",
    )
    narrator_fingerprint_before = backend.profile_fingerprint(registry.get("narrator"))
    assembler = ChapterAudioAssembler(args.output_dir, ffmpeg=ffmpeg, bitrate_kbps=96)

    events: list[dict[str, Any]] = []
    narrator_prompt_hashes: list[str] = []
    started = time.perf_counter()

    def callback(event: str, data: dict[str, object]) -> None:
        events.append({
            "event": event,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            **data,
        })
        print(f"CROSS_CHAPTER_PROGRESS {event} {json.dumps(data, ensure_ascii=False)}", flush=True)

    worker = ChapterWorker(
        document,
        args.output_dir,
        registry,
        attribution,
        backend,
        assembler,
        max_attempts=1,
        callback=callback,
    )

    # Instrument only the stable on-disk prompt identity. Synthesis still delegates
    # unchanged text and profiles to the production QwenVoiceBackend method.
    original_synthesize = backend.synthesize

    def tracked_synthesize(text: str, profile: VoiceProfile):
        if profile.speaker_id == "narrator":
            _reference, prompt_path = backend._paths(profile)
            if not prompt_path.is_file():
                raise RuntimeError("Narrator prompt is missing at cross-chapter synthesis.")
            narrator_prompt_hashes.append(sha256_file(prompt_path))
        return original_synthesize(text, profile)

    backend.synthesize = tracked_synthesize  # type: ignore[method-assign]
    worker.start(background=False)
    if set(worker._chapter_segments) != {("Genesis", 1), ("Genesis", 2)}:
        raise RuntimeError("Worker did not construct speech segments for both test chapters.")
    if worker.error is not None:
        raise RuntimeError(f"Chapter worker failed: {type(worker.error).__name__}: {worker.error}")

    expected_counts = {"pending": 0, "running": 0, "complete": 2, "failed": 0}
    counts = worker.store.progress()
    if counts != expected_counts:
        report_path = args.output_dir / "metadata" / "generation_report.json"
        report = report_path.read_text(encoding="utf-8") if report_path.is_file() else "missing"
        raise RuntimeError(f"Cross-chapter queue did not complete: {counts}; report={report}")

    if len(narrator_prompt_hashes) != 2 or len(set(narrator_prompt_hashes)) != 1:
        raise RuntimeError(
            "Narrator prompt file changed between Genesis 1 and 2 synthesis: "
            f"{narrator_prompt_hashes}"
        )

    preparing_events = [item for item in events if item["event"] == "preparing_voices"]
    if len(preparing_events) != 1:
        raise RuntimeError(f"Expected one batch profile-preparation phase, found {len(preparing_events)}.")
    phase_events = [item for item in events if item["event"] == "voice_profile_progress"]
    design_speakers = sorted(item["speaker_id"] for item in phase_events if item.get("phase") == "voice_design")
    clone_speakers = sorted(item["speaker_id"] for item in phase_events if item.get("phase") == "clone_prompt")
    if design_speakers != ["adam", "narrator"] or clone_speakers != ["adam", "narrator"]:
        raise RuntimeError(
            f"Expected one VoiceDesign and Base prompt per speaker; "
            f"design={design_speakers}, clone={clone_speakers}"
        )

    narrator = registry.get("narrator")
    narrator_fingerprint_after = backend.profile_fingerprint(narrator)
    if narrator_fingerprint_before != narrator_fingerprint_after:
        raise RuntimeError("Narrator voice-profile fingerprint changed during the two-chapter queue.")

    voice_assets = args.output_dir / "metadata" / "voice_assets"
    narrator_reference = voice_assets / "narrator.reference.wav"
    narrator_prompt = voice_assets / "narrator.prompt.pt"
    narrator_prompt_meta_path = voice_assets / "narrator.prompt.json"
    for path in (narrator_reference, narrator_prompt, narrator_prompt_meta_path):
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"Persistent narrator voice asset is missing: {path}")
    prompt_meta = json.loads(narrator_prompt_meta_path.read_text(encoding="utf-8"))
    if prompt_meta.get("prompt_schema_version") != 2:
        raise RuntimeError("Narrator Qwen prompt asset has an unexpected schema version.")
    if prompt_meta.get("profile_signature") != narrator_fingerprint_after:
        raise RuntimeError("Persisted narrator prompt signature does not match the registry profile.")
    if prompt_meta.get("prompt_sha256") != sha256_file(narrator_prompt):
        raise RuntimeError("Persisted narrator prompt file does not match its metadata SHA-256.")

    all_segments: list[dict[str, Any]] = []
    chapter_outputs: list[dict[str, Any]] = []
    for chapter in chapters:
        stem = f"Genesis_{chapter.number:03d}"
        mp3 = args.output_dir / "Genesis" / f"{stem}.mp3"
        cue_path = args.output_dir / "metadata" / "verse_timestamps" / f"{stem}.json"
        for path in (mp3, cue_path):
            if not path.is_file() or path.stat().st_size == 0:
                raise RuntimeError(f"Cross-chapter output is missing or empty: {path}")
        cue_payload = json.loads(cue_path.read_text(encoding="utf-8"))
        if cue_payload.get("book") != "Genesis" or int(cue_payload.get("chapter", -1)) != chapter.number:
            raise RuntimeError(f"Invalid book/chapter metadata in {cue_path.name}.")
        segments = cue_payload.get("segments")
        if not isinstance(segments, list) or not segments:
            raise RuntimeError(f"No cue segments were written for {chapter.label}.")
        grouped: dict[str, list[str]] = {}
        for item in segments:
            reference = item.get("reference")
            if not isinstance(reference, str) or not isinstance(item.get("text"), str):
                raise RuntimeError(f"Malformed cue segment in {cue_path.name}.")
            if float(item.get("end_seconds", 0)) <= float(item.get("start_seconds", 0)):
                raise RuntimeError(f"Invalid cue timing in {cue_path.name}.")
            grouped.setdefault(reference, []).append(item["text"])
        for verse in chapter.verses:
            if "".join(grouped.get(verse.ref.label(), [])) != verse.text:
                raise RuntimeError(f"Cue text differs from exact KJV verse: {verse.ref.label()}.")
        stats = decode_probe(ffmpeg, mp3)
        if abs(stats["decoded_duration_seconds"] - float(cue_payload["duration_seconds"])) > 5.0:
            raise RuntimeError(f"Decoded audio duration does not align with cues for {stem}.")
        all_segments.extend(segments)
        chapter_outputs.append({
            "book": "Genesis",
            "chapter": chapter.number,
            "mp3": str(mp3.relative_to(args.output_dir)),
            "mp3_bytes": mp3.stat().st_size,
            "mp3_sha256": sha256_file(mp3),
            "cue_json": str(cue_path.relative_to(args.output_dir)),
            "cue_json_bytes": cue_path.stat().st_size,
            **stats,
        })

    speaker_counts = {
        speaker: sum(item.get("speaker_id") == speaker for item in all_segments)
        for speaker in ("narrator", "adam")
    }
    if speaker_counts != {"narrator": 2, "adam": 1}:
        raise RuntimeError(f"Unexpected speaker segment counts: {speaker_counts}")
    narrator_refs = [
        item.get("reference")
        for item in all_segments
        if item.get("speaker_id") == "narrator"
    ]
    if narrator_refs != ["Genesis 1:1", "Genesis 2:23"]:
        raise RuntimeError("Narrator did not occur in both chapter outputs in canonical queue order.")

    metrics = {
        "status": "passed",
        "synthetic_test_backend": False,
        "pipeline": "one ChapterWorker + one QwenVoiceBackend across Genesis 1 and Genesis 2",
        "qwen_package": importlib.metadata.version("qwen-tts"),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "device": args.device,
        "offline_inference": True,
        "model_integrity_report": integrity_rows,
        "fixture": str(source.relative_to(project_root)),
        "source_verses": [verse.ref.label() for chapter in chapters for verse in chapter.verses],
        "complete_queue_counts": counts,
        "profile_preparation_batches": len(preparing_events),
        "voice_design_speakers": design_speakers,
        "clone_prompt_speakers": clone_speakers,
        "speaker_segment_counts": speaker_counts,
        "narrator_profile_fingerprint_before": narrator_fingerprint_before,
        "narrator_profile_fingerprint_after": narrator_fingerprint_after,
        "narrator_prompt_sha256_by_chapter_synthesis": narrator_prompt_hashes,
        "narrator_prompt_sha256": prompt_meta["prompt_sha256"],
        "narrator_reference_sha256": sha256_file(narrator_reference),
        "chapter_outputs": chapter_outputs,
        "events": events,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    report_path = args.output_dir / "qwen_real_cross_chapter_voice_metrics.json"
    report_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2, ensure_ascii=False), flush=True)
    print("GENUINE_QWEN_CROSS_CHAPTER_VOICE_IDENTITY_PASSED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
