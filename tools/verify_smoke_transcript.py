from __future__ import annotations

import argparse
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

MODEL_ID = "openai/whisper-tiny.en"
MODEL_REVISION = "87c7102498dcde7456f24cfd30239ca606ed9063"
TAIL_WORD_COUNT = 5
MIN_TEXT_SIMILARITY = 0.80


def normalized_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(text).casefold())


def assess_transcript(expected_text: str, recognized_text: str) -> dict[str, Any]:
    expected_words = normalized_words(expected_text)
    recognized_words = normalized_words(recognized_text)
    tail_words = expected_words[-TAIL_WORD_COUNT:]
    tail_present = bool(tail_words) and any(
        recognized_words[index:index + len(tail_words)] == tail_words
        for index in range(max(0, len(recognized_words) - len(tail_words) + 1))
    )
    similarity = (
        SequenceMatcher(a=expected_words, b=recognized_words).ratio()
        if expected_words and recognized_words else 0.0
    )
    passed = bool(expected_words and recognized_words and tail_present and similarity >= MIN_TEXT_SIMILARITY)
    return {
        "passed": passed,
        "normalized_expected": " ".join(expected_words),
        "normalized_recognized": " ".join(recognized_words),
        "similarity_ratio": round(similarity, 4),
        "required_trailing_phrase": " ".join(tail_words),
        "trailing_phrase_present": tail_present,
        "minimum_similarity_ratio": MIN_TEXT_SIMILARITY,
    }


def transcribe_audio(audio_path: Path, processor: Any, model: Any, torch: Any, torchaudio: Any) -> dict[str, Any]:
    import numpy as np
    import soundfile as sf

    if not audio_path.is_file():
        raise FileNotFoundError(f"Decoded MP3 WAV does not exist: {audio_path}")
    waveform_np, sample_rate = sf.read(audio_path, dtype="float32", always_2d=False)
    waveform_np = np.asarray(waveform_np, dtype=np.float32)
    if waveform_np.ndim == 2:
        waveform_np = waveform_np.mean(axis=1, dtype=np.float32)
    if waveform_np.ndim != 1 or waveform_np.size == 0:
        raise RuntimeError(f"Audio is empty or has an unsupported shape: {audio_path}")
    if not np.isfinite(waveform_np).all():
        raise RuntimeError(f"Audio contains non-finite samples: {audio_path}")

    waveform = torch.from_numpy(waveform_np)
    if int(sample_rate) != 16000:
        waveform = torchaudio.functional.resample(
            waveform, orig_freq=int(sample_rate), new_freq=16000
        )
    audio_16k = waveform.cpu().numpy()
    features = processor(
        audio_16k,
        sampling_rate=16000,
        return_tensors="pt",
    ).input_features
    with torch.inference_mode():
        predicted_ids = model.generate(
            features,
            do_sample=False,
            num_beams=3,
            max_new_tokens=96,
        )
    transcript = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0].strip()
    return {
        "audio_file": str(audio_path),
        "input_sample_rate": int(sample_rate),
        "input_duration_seconds": round(float(waveform_np.size) / float(sample_rate), 3),
        "recognized_text": transcript,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify that the final packaged Qwen MP3s contain the complete expected spoken sentence."
    )
    parser.add_argument("--audio", action="append", type=Path, required=True,
                        help="A WAV decoded from the final MP3. Repeat for each package location.")
    parser.add_argument("--expected-text", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--acceptance-summary", type=Path)
    args = parser.parse_args()

    report: dict[str, Any] = {
        "status": "failed",
        "model": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "model_license": "Apache-2.0",
        "expected_text": args.expected_text,
        "checks": [],
        "note": (
            "ASR is an independent automated signal, not proof of perfect transcription. "
            "Keep human listening QA as a separate release requirement."
        ),
    }
    try:
        import torch
        import torchaudio
        from transformers import WhisperForConditionalGeneration, WhisperProcessor

        torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
        processor = WhisperProcessor.from_pretrained(
            MODEL_ID,
            revision=MODEL_REVISION,
        )
        model = WhisperForConditionalGeneration.from_pretrained(
            MODEL_ID,
            revision=MODEL_REVISION,
            use_safetensors=True,
        ).to("cpu").eval()

        for audio_path in args.audio:
            result = transcribe_audio(audio_path, processor, model, torch, torchaudio)
            assessment = assess_transcript(args.expected_text, result["recognized_text"])
            report["checks"].append({**result, **assessment})
        report["status"] = (
            "passed" if report["checks"] and all(item["passed"] for item in report["checks"])
            else "failed"
        )
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)
        report["status"] = "failed"

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.acceptance_summary:
        try:
            summary = json.loads(args.acceptance_summary.read_text(encoding="utf-8"))
            summary["speech_transcript_check"] = report["status"]
            summary["speech_transcript_model"] = f"{MODEL_ID}@{MODEL_REVISION}"
            args.acceptance_summary.write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except Exception as exc:
            print(f"Could not update the package acceptance summary: {exc}", file=sys.stderr)
            return 2

    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)
    if report["status"] != "passed":
        print("PACKAGED_QWEN_SPEECH_TRANSCRIPT_FAILED", file=sys.stderr, flush=True)
        return 1
    print("PACKAGED_QWEN_SPEECH_TRANSCRIPT_PASSED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
