from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from kjv_audio_generator.attribution import AttributionMap
from kjv_audio_generator.audio import ChapterAudioAssembler
from kjv_audio_generator.backend import QwenSettings, QwenVoiceBackend
from kjv_audio_generator.parser import parse_path
from kjv_audio_generator.voices import VoiceRegistry
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


def verify_integrity_report(path: Path) -> list[dict[str, Any]]:
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read the pinned Qwen integrity report: {exc}") from exc
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


def probe_mp3(ffmpeg: str, path: Path) -> dict[str, float | int]:
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(path),
        "-ac",
        "1",
        "-ar",
        "24000",
        "-f",
        "f32le",
        "pipe:1",
    ]
    result = subprocess.run(command, capture_output=True, timeout=240, check=False)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace")[-2000:]
        raise RuntimeError(f"FFmpeg could not decode the generated Genesis 1 MP3: {detail}")
    if len(result.stdout) < 4 or len(result.stdout) % 4:
        raise RuntimeError("FFmpeg returned an invalid PCM byte count for Genesis 1.")
    samples = np.frombuffer(result.stdout, dtype="<f4")
    if samples.size == 0 or not np.isfinite(samples).all():
        raise RuntimeError("Decoded Genesis 1 audio is empty or contains non-finite samples.")
    peak = float(np.max(np.abs(samples)))
    rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))
    duration = float(samples.size) / 24000.0
    if peak < 0.005 or rms < 0.0005:
        raise RuntimeError(f"Genesis 1 decoded MP3 appears silent: peak={peak:.6f}, rms={rms:.6f}.")
    if peak > 1.2:
        raise RuntimeError(f"Genesis 1 decoded MP3 appears clipped: peak={peak:.6f}.")
    return {
        "decoded_sample_rate": 24000,
        "decoded_frames": int(samples.size),
        "decoded_duration_seconds": round(duration, 3),
        "decoded_peak": round(peak, 6),
        "decoded_rms": round(rms, 6),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate real Qwen Genesis 1 MP3, manual speaker segments and timestamp cues."
    )
    parser.add_argument("--models-root", type=Path, required=True)
    parser.add_argument("--integrity-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu",), default="cpu")
    parser.add_argument("--ffmpeg", type=str, default=None)
    args = parser.parse_args()

    for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE"):
        if os.environ.get(name) not in {"1", "true", "TRUE"}:
            raise RuntimeError(f"{name}=1 is required for local-only Genesis 1 model inference.")

    integrity_rows = verify_integrity_report(args.integrity_report)
    ffmpeg = args.ffmpeg or shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg was not found; the real Genesis 1 MP3 pipeline cannot run.")

    project_root = Path(__file__).resolve().parents[1]
    source = project_root / "examples" / "genesis_1_kjv_test.txt"
    if not source.is_file():
        raise RuntimeError(f"The full 31-verse Genesis 1 fixture is missing: {source}")
    document = parse_path(source)
    chapter = document.chapter("Genesis", 1)
    if len(chapter.verses) != 31:
        raise RuntimeError(f"Genesis 1 fixture has {len(chapter.verses)} verses; expected 31.")
    if chapter.verses[0].text != "In the beginning God created the heaven and the earth.":
        raise RuntimeError("Genesis 1 fixture opening verse did not match the expected KJV text.")
    if "sixth day" not in chapter.verses[-1].text:
        raise RuntimeError("Genesis 1 fixture final verse did not match the expected KJV text.")

    # KJV prose has no quotation marks around all spoken lines. For this acceptance
    # sample the two quoted speech segments are deliberately and explicitly reviewed:
    # the narrator introduces God's words, and God speaks the quotation itself.
    overrides = {
        "Genesis 1:3": [
            {"speaker_id": "narrator", "text": "And God said, "},
            {"speaker_id": "god", "text": "Let there be light: and there was light."},
        ],
        "Genesis 1:6": [
            {"speaker_id": "narrator", "text": "And God said, "},
            {
                "speaker_id": "god",
                "text": "Let there be a firmament in the midst of the waters, and let it divide the waters from the waters.",
            },
        ],
    }
    for verse in chapter.verses:
        if verse.ref.label() in overrides:
            combined = "".join(segment["text"] for segment in overrides[verse.ref.label()])
            if combined != verse.text:
                raise RuntimeError(f"Manual speaker split does not preserve exact KJV text in {verse.ref.label()}.")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    registry = VoiceRegistry.defaults()
    attribution = AttributionMap(registry, segment_overrides=overrides)
    models_root = args.models_root.resolve()
    backend = QwenVoiceBackend(
        QwenSettings(
            voice_design_model=models_root / "Qwen3-TTS-12Hz-1.7B-VoiceDesign",
            base_model=models_root / "Qwen3-TTS-12Hz-1.7B-Base",
            device=args.device,
            language="English",
        ),
        args.output_dir / "metadata" / "voice_assets",
    )
    assembler = ChapterAudioAssembler(args.output_dir, ffmpeg=ffmpeg, bitrate_kbps=96)

    events: list[dict[str, Any]] = []
    started = time.perf_counter()

    def callback(event: str, data: dict[str, object]) -> None:
        events.append({
            "event": event,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            **data,
        })
        print(f"GENESIS1_PROGRESS {event} {json.dumps(data, ensure_ascii=False)}", flush=True)

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
    worker.start(background=False)
    if worker.error is not None:
        raise RuntimeError(f"Chapter worker failed: {type(worker.error).__name__}: {worker.error}")

    counts = worker.store.progress()
    expected_counts = {"pending": 0, "running": 0, "complete": 1, "failed": 0}
    if counts != expected_counts:
        report_path = args.output_dir / "metadata" / "generation_report.json"
        report = report_path.read_text(encoding="utf-8") if report_path.is_file() else "missing"
        raise RuntimeError(f"Genesis 1 chapter did not complete successfully: {counts}; report={report}")

    mp3 = args.output_dir / "Genesis" / "Genesis_001.mp3"
    cue_path = args.output_dir / "metadata" / "verse_timestamps" / "Genesis_001.json"
    for path in (mp3, cue_path):
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"Real Genesis 1 output is missing or empty: {path}")

    cues = json.loads(cue_path.read_text(encoding="utf-8"))
    segments = cues.get("segments")
    if cues.get("book") != "Genesis" or cues.get("chapter") != 1 or not isinstance(segments, list):
        raise RuntimeError("Genesis 1 cue JSON has an invalid book/chapter/segment structure.")
    if len(segments) != 33:
        raise RuntimeError(f"Genesis 1 cue file has {len(segments)} segments; expected 33.")
    if sum(item.get("speaker_id") == "god" for item in segments) != 2:
        raise RuntimeError("Genesis 1 should contain exactly two manually reviewed God speech segments.")
    if sum(item.get("speaker_id") == "narrator" for item in segments) != 31:
        raise RuntimeError("Genesis 1 should contain exactly 31 narrator segments.")
    grouped_text: dict[str, list[str]] = {}
    for item in segments:
        reference = item.get("reference")
        text = item.get("text")
        if not isinstance(reference, str) or not isinstance(text, str):
            raise RuntimeError("Genesis 1 cue segment is missing its exact verse reference or text.")
        if float(item.get("end_seconds", 0)) <= float(item.get("start_seconds", 0)):
            raise RuntimeError(f"Genesis 1 cue timing is invalid for {reference}.")
        grouped_text.setdefault(reference, []).append(text)
    for verse in chapter.verses:
        joined = "".join(grouped_text.get(verse.ref.label(), []))
        if joined != verse.text:
            raise RuntimeError(f"Generated cue text did not preserve the exact KJV verse in {verse.ref.label()}.")

    audio_stats = probe_mp3(ffmpeg, mp3)
    last_cue_end = float(segments[-1]["end_seconds"])
    if abs(audio_stats["decoded_duration_seconds"] - last_cue_end) > 5.0:
        raise RuntimeError("Genesis 1 MP3 decoded duration differs from final cue timing by more than five seconds.")

    voice_assets = args.output_dir / "metadata" / "voice_assets"
    required_voice_assets = [
        voice_assets / "narrator.reference.wav",
        voice_assets / "narrator.prompt.pt",
        voice_assets / "narrator.prompt.prompt.json",
        voice_assets / "god.reference.wav",
        voice_assets / "god.prompt.pt",
        voice_assets / "god.prompt.prompt.json",
    ]
    for path in required_voice_assets:
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"Required real speaker voice asset is missing or empty: {path}")

    metrics = {
        "status": "passed",
        "synthetic_test_backend": False,
        "pipeline": "ChapterWorker + QwenVoiceBackend + ChapterAudioAssembler",
        "qwen_package": importlib.metadata.version("qwen-tts"),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "device": args.device,
        "offline_inference": True,
        "model_integrity_report": integrity_rows,
        "source_fixture": str(source.relative_to(project_root)),
        "source_verse_count": len(chapter.verses),
        "output_segment_count": len(segments),
        "speaker_segment_counts": {
            "narrator": sum(item.get("speaker_id") == "narrator" for item in segments),
            "god": sum(item.get("speaker_id") == "god" for item in segments),
        },
        "progress_events": events,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "output_mp3": str(mp3.relative_to(args.output_dir)),
        "output_mp3_bytes": mp3.stat().st_size,
        "cue_json": str(cue_path.relative_to(args.output_dir)),
        "cue_json_bytes": cue_path.stat().st_size,
        "ffmpeg_path": ffmpeg,
        **audio_stats,
    }
    metrics_path = args.output_dir / "qwen_real_genesis1_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2, ensure_ascii=False), flush=True)
    print("GENUINE_QWEN_GENESIS1_PIPELINE_PASSED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
