from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

MODEL_ID = "openai/whisper-tiny.en"
MODEL_REVISION = "87c7102498dcde7456f24cfd30239ca606ed9063"
MIN_TEXT_SIMILARITY = 0.70
PREFIX_WORD_COUNT = 8
TAIL_WORD_COUNT = 8


def normalized_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(text).casefold())


def validate_chapter_cues(source_path: Path, cue_path: Path) -> dict[str, Any]:
    """Verify every Genesis 1 cue reconstructs its exact source verse, in order."""
    from kjv_audio_generator.parser import parse_path

    document = parse_path(source_path)
    chapter = document.chapter("Genesis", 1)
    if len(chapter.verses) != 31:
        raise ValueError(f"Genesis 1 source has {len(chapter.verses)} verses; expected 31.")

    payload = json.loads(cue_path.read_text(encoding="utf-8-sig"))
    if payload.get("book") != "Genesis" or payload.get("chapter") != 1:
        raise ValueError("Cue file does not identify Genesis chapter 1.")
    segments = payload.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError("Genesis 1 cue file has no speech segments.")

    grouped: dict[str, list[str]] = {}
    first_seen: list[str] = []
    previous_end = 0.0
    for item in segments:
        if not isinstance(item, dict):
            raise ValueError("Cue segment is not an object.")
        reference = item.get("reference")
        text = item.get("text")
        if not isinstance(reference, str) or not isinstance(text, str):
            raise ValueError("Cue segment is missing its verse reference or speech text.")
        if reference not in grouped:
            grouped[reference] = []
            first_seen.append(reference)
        grouped[reference].append(text)
        start = float(item.get("start_seconds", 0))
        end = float(item.get("end_seconds", 0))
        if start < previous_end - 0.01 or end <= start:
            raise ValueError(f"Invalid or overlapping cue timing for {reference}: {start} to {end}.")
        previous_end = end

    cue_duration = float(payload.get("duration_seconds", 0))
    if cue_duration <= 0 or abs(previous_end - cue_duration) > 0.05:
        raise ValueError(
            f"Genesis 1 cue duration ({cue_duration}) does not match the final speech cue ({previous_end})."
        )

    expected_refs = [verse.ref.label() for verse in chapter.verses]
    if first_seen != expected_refs:
        missing = [reference for reference in expected_refs if reference not in grouped]
        unexpected = [reference for reference in first_seen if reference not in set(expected_refs)]
        raise ValueError(
            f"Cue verse coverage/order does not match Genesis 1; missing={missing}, unexpected={unexpected}."
        )

    verse_texts: list[str] = []
    for verse in chapter.verses:
        actual = "".join(grouped[verse.ref.label()])
        if actual != verse.text:
            raise ValueError(
                f"Cue speech text does not exactly match source for {verse.ref.label()}."
            )
        verse_texts.append(actual)

    expected_text = " ".join(verse_texts)
    return {
        "expected_text": expected_text,
        "expected_word_count": len(normalized_words(expected_text)),
        "source_verse_count": len(chapter.verses),
        "cue_segment_count": len(segments),
        "unique_verse_count": len(grouped),
        "expected_text_sha256": hashlib.sha256(expected_text.encode("utf-8")).hexdigest(),
        "expected_prefix": " ".join(normalized_words(expected_text)[:PREFIX_WORD_COUNT]),
        "required_trailing_phrase": " ".join(normalized_words(expected_text)[-TAIL_WORD_COUNT:]),
        "duration_seconds": float(payload.get("duration_seconds", 0)),
    }


def assess_chapter_transcript(
    expected_text: str,
    recognized_text: str,
    *,
    minimum_similarity: float = MIN_TEXT_SIMILARITY,
) -> dict[str, Any]:
    expected_words = normalized_words(expected_text)
    recognized_words = normalized_words(recognized_text)
    prefix = expected_words[:PREFIX_WORD_COUNT]
    tail = expected_words[-TAIL_WORD_COUNT:]
    prefix_present = bool(prefix) and any(
        recognized_words[index:index + len(prefix)] == prefix
        for index in range(max(0, len(recognized_words) - len(prefix) + 1))
    )
    tail_present = bool(tail) and any(
        recognized_words[index:index + len(tail)] == tail
        for index in range(max(0, len(recognized_words) - len(tail) + 1))
    )
    similarity = (
        SequenceMatcher(a=expected_words, b=recognized_words, autojunk=False).ratio()
        if expected_words and recognized_words else 0.0
    )
    return {
        "passed": bool(
            expected_words and recognized_words
            and prefix_present and tail_present
            and similarity >= minimum_similarity
        ),
        "expected_word_count": len(expected_words),
        "recognized_word_count": len(recognized_words),
        "similarity_ratio": round(similarity, 4),
        "minimum_similarity_ratio": minimum_similarity,
        "prefix_phrase": " ".join(prefix),
        "prefix_phrase_present": prefix_present,
        "required_trailing_phrase": " ".join(tail),
        "trailing_phrase_present": tail_present,
    }


def decode_audio_16khz(path: Path, ffmpeg: str) -> Any:
    import numpy as np

    if not path.is_file():
        raise FileNotFoundError(f"Genesis 1 MP3 does not exist: {path}")
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(path),
        "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "pipe:1",
    ]
    result = subprocess.run(command, capture_output=True, timeout=300, check=False)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace")[-2000:]
        raise RuntimeError(f"FFmpeg could not decode Genesis 1 MP3: {detail}")
    if not result.stdout or len(result.stdout) % 4:
        raise RuntimeError("FFmpeg returned empty or malformed Genesis 1 PCM data.")
    audio = np.frombuffer(result.stdout, dtype="<f4").copy()
    if audio.size == 0 or not np.isfinite(audio).all():
        raise RuntimeError("Decoded Genesis 1 waveform is empty or non-finite.")
    return audio


def transcribe_long_audio(audio: Any) -> str:
    import torch
    from transformers import WhisperForConditionalGeneration, WhisperProcessor

    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
    processor = WhisperProcessor.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
    model = WhisperForConditionalGeneration.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        use_safetensors=True,
    ).to("cpu").eval()

    # Whisper's long-form path requires the complete, untruncated feature sequence
    # and return_timestamps=True; this lets Whisper advance through the chapter.
    inputs = processor(
        audio,
        sampling_rate=16000,
        return_tensors="pt",
        truncation=False,
        padding="longest",
        return_attention_mask=True,
    )
    with torch.inference_mode():
        generated_ids = model.generate(**inputs, return_timestamps=True)
    return processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the spoken content of the complete 31-verse Genesis 1 Qwen chapter MP3."
    )
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--cue", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--ffmpeg", default=None)
    parser.add_argument("--minimum-similarity", type=float, default=MIN_TEXT_SIMILARITY)
    args = parser.parse_args()

    report: dict[str, Any] = {
        "status": "failed",
        "model": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "model_license": "Apache-2.0",
        "minimum_similarity_ratio": args.minimum_similarity,
        "checks": {},
        "note": (
            "Long-form Whisper recognition is an independent automated signal, not proof of perfect "
            "transcription or listening quality. Human listening QA remains separate."
        ),
    }
    try:
        if not 0.0 < args.minimum_similarity <= 1.0:
            raise ValueError("--minimum-similarity must be greater than 0 and at most 1.")
        source_check = validate_chapter_cues(args.source, args.cue)
        ffmpeg = args.ffmpeg or shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("FFmpeg is required to decode the Genesis 1 MP3 for transcription.")
        audio = decode_audio_16khz(args.audio, ffmpeg)
        duration = float(audio.size) / 16000.0
        recognized = transcribe_long_audio(audio)
        assessment = assess_chapter_transcript(
            source_check["expected_text"],
            recognized,
            minimum_similarity=args.minimum_similarity,
        )
        report.update({
            "status": "passed" if assessment["passed"] else "failed",
            "audio_file": str(args.audio),
            "audio_duration_seconds": round(duration, 3),
            "source_file": str(args.source),
            "cue_file": str(args.cue),
            "source_verse_count": source_check["source_verse_count"],
            "cue_segment_count": source_check["cue_segment_count"],
            "expected_text_sha256": source_check["expected_text_sha256"],
            "recognized_text": recognized,
            "checks": {**source_check, **assessment},
        })
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)
        report["status"] = "failed"

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)
    if report["status"] != "passed":
        print("GENESIS1_SPEECH_TRANSCRIPT_FAILED", file=sys.stderr, flush=True)
        return 1
    print("GENESIS1_SPEECH_TRANSCRIPT_PASSED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
