from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
import torch

# The project adapter is the production Qwen path, not a mock or synthetic backend.
from kjv_audio_generator.backend import QwenSettings, QwenVoiceBackend
from kjv_audio_generator.voices import VoiceProfile

EXPECTED_MODELS = {
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


def load_integrity_report(path: Path) -> list[dict[str, Any]]:
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read the completed model SHA-256 report: {exc}") from exc
    if not isinstance(rows, list) or len(rows) != 2:
        raise RuntimeError("Model integrity report must contain exactly two verified snapshots.")
    by_repo = {row.get("repo"): row for row in rows if isinstance(row, dict)}
    if set(by_repo) != set(EXPECTED_MODELS):
        raise RuntimeError("Model integrity report does not identify both exact pinned Qwen snapshots.")
    for repo, expected in EXPECTED_MODELS.items():
        row = by_repo[repo]
        for field, expected_value in expected.items():
            actual_value = row.get(field)
            if actual_value != expected_value:
                raise RuntimeError(
                    f"Model integrity report mismatch for {repo} field {field}: "
                    f"expected {expected_value}, got {actual_value}"
                )
    return rows


def peak_rss_mib() -> float | None:
    try:
        import resource
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Linux reports KiB; macOS reports bytes. This workflow is Linux but keep the helper explicit.
        if sys.platform.startswith("linux"):
            return round(float(value) / 1024.0, 1)
        return round(float(value) / (1024.0 * 1024.0), 1)
    except (ImportError, OSError, ValueError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a genuine CPU-only Qwen3-TTS VoiceDesign -> Base inference smoke test."
    )
    parser.add_argument("--models-root", type=Path, required=True)
    parser.add_argument("--integrity-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu",), default="cpu")
    args = parser.parse_args()

    if os.environ.get("HF_HUB_OFFLINE") not in {"1", "true", "TRUE"}:
        raise RuntimeError("Set HF_HUB_OFFLINE=1 before running inference; online model fallback is not allowed.")
    if os.environ.get("TRANSFORMERS_OFFLINE") not in {"1", "true", "TRUE"}:
        raise RuntimeError("Set TRANSFORMERS_OFFLINE=1 before running inference; online fallback is not allowed.")

    models_root = args.models_root.resolve()
    design_path = models_root / "Qwen3-TTS-12Hz-1.7B-VoiceDesign"
    base_path = models_root / "Qwen3-TTS-12Hz-1.7B-Base"
    integrity_rows = load_integrity_report(args.integrity_report)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    voice_assets = args.output_dir / "voice_assets"
    profile = VoiceProfile(
        speaker_id="qwen_real_cpu_smoke",
        display_name="Qwen Real CPU Smoke",
        aliases=[],
        voice_description=(
            "A warm, mature, clear male reading voice with a calm measured pace, "
            "natural phrasing, precise consonants and restrained expression."
        ),
        reference_text="The Lord is my shepherd; I shall not want.",
    )

    events: list[dict[str, Any]] = []
    started = time.perf_counter()

    def progress(phase: str, index: int, total: int, speaker_id: str) -> None:
        events.append({
            "phase": phase,
            "index": index,
            "total": total,
            "speaker_id": speaker_id,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        })
        print(f"QWEN_PROGRESS {phase} {index}/{total} {speaker_id}", flush=True)

    backend = QwenVoiceBackend(
        QwenSettings(
            voice_design_model=design_path,
            base_model=base_path,
            device=args.device,
            language="English",
        ),
        voice_assets,
    )
    prep_started = time.perf_counter()
    backend.prepare_profiles([profile], progress_callback=progress)
    prepare_seconds = time.perf_counter() - prep_started

    if backend._design_model is not None:
        raise RuntimeError("VoiceDesign model remained resident after prompt preparation; expected it to be released before Base.")
    if backend._base_model is None:
        raise RuntimeError("The real Base Qwen model was not loaded by prepare_profiles().")

    synthesis_text = "In the beginning God created the heaven and the earth."
    synthesis_started = time.perf_counter()
    audio, sample_rate = backend.synthesize(synthesis_text, profile)
    synthesis_seconds = time.perf_counter() - synthesis_started

    audio = np.asarray(audio, dtype=np.float32).reshape(-1)
    if audio.size == 0 or not np.isfinite(audio).all():
        raise RuntimeError("Real Qwen inference returned empty or non-finite audio.")
    peak = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))
    duration_seconds = float(audio.size) / float(sample_rate)
    if sample_rate != 24000:
        raise RuntimeError(f"Unexpected Qwen sample rate: {sample_rate}; expected 24000 Hz.")
    if duration_seconds < 0.5 or duration_seconds > 60.0:
        raise RuntimeError(f"Generated speech duration is outside the smoke-test limits: {duration_seconds:.3f}s.")
    if peak < 0.005 or rms < 0.0005:
        raise RuntimeError(f"Generated speech is silent or too quiet: peak={peak:.6f}, rms={rms:.6f}.")
    if peak > 1.2:
        raise RuntimeError(f"Generated waveform is unexpectedly clipped: peak={peak:.6f}.")

    wav_path = args.output_dir / "qwen_real_speech.wav"
    sf.write(wav_path, audio, sample_rate, subtype="PCM_16")
    reread, reread_rate = sf.read(wav_path, dtype="float32")
    if reread_rate != sample_rate or reread.size != audio.size:
        raise RuntimeError("Saved Qwen WAV did not round-trip through SoundFile with matching rate/frame count.")
    if not np.isfinite(reread).all() or float(np.max(np.abs(reread))) < 0.005:
        raise RuntimeError("Saved Qwen WAV is invalid or silent.")

    reference_path = voice_assets / f"{profile.speaker_id}.reference.wav"
    prompt_path = voice_assets / f"{profile.speaker_id}.prompt.pt"
    prompt_meta = prompt_path.with_suffix(".prompt.json")
    for artifact in (reference_path, prompt_path, prompt_meta, wav_path):
        if not artifact.is_file() or artifact.stat().st_size == 0:
            raise RuntimeError(f"Real Qwen smoke output is missing or empty: {artifact}")

    try:
        qwen_version = importlib.metadata.version("qwen-tts")
    except importlib.metadata.PackageNotFoundError:
        qwen_version = "unknown"

    metrics = {
        "status": "passed",
        "synthetic_test_backend": False,
        "backend": "QwenVoiceBackend",
        "qwen_package": qwen_version,
        "torch_version": torch.__version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "device": args.device,
        "offline_inference": True,
        "model_integrity_report": integrity_rows,
        "speaker_id": profile.speaker_id,
        "voice_design_and_prompt_events": events,
        "profile_preparation_seconds": round(prepare_seconds, 3),
        "speech_synthesis_seconds": round(synthesis_seconds, 3),
        "speech_duration_seconds": round(duration_seconds, 3),
        "speech_real_time_factor": round(synthesis_seconds / duration_seconds, 3),
        "sample_rate": sample_rate,
        "frames": int(audio.size),
        "peak": round(peak, 6),
        "rms": round(rms, 6),
        "process_peak_rss_mib": peak_rss_mib(),
        "voice_design_reference_wav_bytes": reference_path.stat().st_size,
        "voice_clone_prompt_bytes": prompt_path.stat().st_size,
        "output_wav": wav_path.name,
        "output_wav_bytes": wav_path.stat().st_size,
        "text": synthesis_text,
    }
    metrics_path = args.output_dir / "qwen_real_inference_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2, ensure_ascii=False), flush=True)
    print("GENUINE_QWEN_CPU_INFERENCE_SMOKE_PASSED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
