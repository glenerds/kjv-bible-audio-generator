from __future__ import annotations

import contextlib
import json
import sys
import types
from pathlib import Path

import numpy as np
import pytest

from kjv_audio_generator.parser import parse_path
from tools.verify_chapter_transcript import (
    assess_chapter_transcript,
    transcribe_long_audio,
    validate_chapter_cues,
)

ROOT = Path(__file__).resolve().parents[1]
GENESIS_SOURCE = ROOT / "examples" / "genesis_1_kjv_test.txt"


def _make_cue(chapter, *, split_verse: bool = False) -> dict:
    segments = []
    cursor = 0.0
    for verse in chapter.verses:
        parts = [verse.text]
        if split_verse and verse.ref.label() == "Genesis 1:3":
            parts = ["And God said, ", "Let there be light: and there was light."]
        for part in parts:
            start = cursor
            end = start + 0.5
            segments.append({
                "reference": verse.ref.label(),
                "text": part,
                "start_seconds": round(start, 3),
                "end_seconds": round(end, 3),
            })
            cursor = end + 0.12
    return {
        "book": "Genesis",
        "chapter": 1,
        "duration_seconds": segments[-1]["end_seconds"],
        "segments": segments,
    }


def test_genesis_one_cues_reconstruct_all_31_source_verses_exactly(tmp_path):
    chapter = parse_path(GENESIS_SOURCE).chapter("Genesis", 1)
    cue_path = tmp_path / "genesis1-cues.json"
    cue_path.write_text(json.dumps(_make_cue(chapter)), encoding="utf-8")

    result = validate_chapter_cues(GENESIS_SOURCE, cue_path)

    assert result["source_verse_count"] == 31
    assert result["unique_verse_count"] == 31
    assert result["cue_segment_count"] == 31
    assert result["required_trailing_phrase"].endswith("sixth day")


def test_genesis_one_cue_validation_rejects_missing_verse(tmp_path):
    chapter = parse_path(GENESIS_SOURCE).chapter("Genesis", 1)
    cue = _make_cue(chapter)
    cue["segments"] = cue["segments"][:-1]
    cue["duration_seconds"] = cue["segments"][-1]["end_seconds"]
    cue_path = tmp_path / "missing.json"
    cue_path.write_text(json.dumps(cue), encoding="utf-8")

    with pytest.raises(ValueError, match="coverage/order"):
        validate_chapter_cues(GENESIS_SOURCE, cue_path)


def test_genesis_one_cue_validation_accepts_split_verse_segments(tmp_path):
    chapter = parse_path(GENESIS_SOURCE).chapter("Genesis", 1)
    cue_path = tmp_path / "genesis1-split-cues.json"
    cue_path.write_text(
        json.dumps(_make_cue(chapter, split_verse=True)),
        encoding="utf-8",
    )

    result = validate_chapter_cues(GENESIS_SOURCE, cue_path)

    assert result["cue_segment_count"] == 32
    assert result["source_verse_count"] == 31


def test_genesis_one_cue_validation_rejects_overlapping_or_nonchronological_cues(tmp_path):
    chapter = parse_path(GENESIS_SOURCE).chapter("Genesis", 1)
    cue = _make_cue(chapter)
    cue["segments"][1]["start_seconds"] = 0.25
    cue["segments"][1]["end_seconds"] = 0.75
    cue_path = tmp_path / "overlap.json"
    cue_path.write_text(json.dumps(cue), encoding="utf-8")

    with pytest.raises(ValueError, match="overlapping cue timing"):
        validate_chapter_cues(GENESIS_SOURCE, cue_path)


def test_long_form_chapter_transcript_requires_opening_and_final_verse():
    expected = (
        "In the beginning God created the heaven and the earth. "
        "And God saw every thing that he had made, and, behold, it was very good. "
        "And the evening and the morning were the sixth day."
    )
    complete = assess_chapter_transcript(expected, expected, minimum_similarity=0.70)
    assert complete["passed"] is True
    assert complete["prefix_phrase_present"] is True
    assert complete["trailing_phrase_present"] is True

    truncated = assess_chapter_transcript(
        expected,
        "In the beginning God created the heaven and the earth. "
        "And God saw every thing that he had made, and, behold, it was very good.",
        minimum_similarity=0.70,
    )
    assert truncated["passed"] is False
    assert truncated["trailing_phrase_present"] is False


def test_long_form_chapter_transcript_rejects_unrelated_or_too_short_text():
    result = assess_chapter_transcript(
        "In the beginning God created the heaven and the earth.",
        "This is a test of the King James Bible narrator voice.",
        minimum_similarity=0.70,
    )
    assert result["passed"] is False


def test_long_form_transcriber_uses_whisper_native_long_audio_mode(monkeypatch):
    calls = {}

    class FakeProcessor:
        @classmethod
        def from_pretrained(cls, model_id, revision):
            calls["processor_model"] = (model_id, revision)
            return cls()

        def __call__(self, audio, **kwargs):
            calls["audio_samples"] = len(audio)
            calls["processor_kwargs"] = kwargs
            return {"input_features": "features", "attention_mask": "mask"}

        def batch_decode(self, generated_ids, skip_special_tokens):
            calls["decoded_ids"] = generated_ids
            calls["skip_special_tokens"] = skip_special_tokens
            return ["complete long-form transcript"]

    class FakeModel:
        @classmethod
        def from_pretrained(cls, model_id, **kwargs):
            calls["model_load"] = (model_id, kwargs)
            return cls()

        def to(self, device):
            calls["device"] = device
            return self

        def eval(self):
            calls["eval"] = True
            return self

        def generate(self, **kwargs):
            calls["generate_kwargs"] = kwargs
            return ["generated-token-ids"]

    fake_torch = types.SimpleNamespace(
        get_num_threads=lambda: 8,
        set_num_threads=lambda count: calls.setdefault("torch_threads", count),
        inference_mode=contextlib.nullcontext,
    )
    fake_transformers = types.SimpleNamespace(
        WhisperForConditionalGeneration=FakeModel,
        WhisperProcessor=FakeProcessor,
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)

    result = transcribe_long_audio(np.zeros(16000, dtype=np.float32))

    assert result == "complete long-form transcript"
    assert calls["processor_kwargs"]["truncation"] is False
    assert calls["processor_kwargs"]["return_attention_mask"] is True
    assert calls["generate_kwargs"]["return_timestamps"] is True
    assert calls["generate_kwargs"]["input_features"] == "features"
    assert calls["generate_kwargs"]["attention_mask"] == "mask"


def test_genesis_transcript_failure_still_preserves_audio_and_cross_chapter_evidence():
    workflow = (
        ROOT / ".github" / "workflows" / "qwen-real-inference.yml"
    ).read_text(encoding="utf-8")

    verify_name = "- name: Verify complete Genesis 1 narration with pinned long-form Whisper"
    upload_genesis_name = "- name: Upload genuine Genesis 1 MP3 and speech-verification evidence"
    cross_chapter_name = "- name: Run real Qwen narrator identity check across Genesis 1 and 2 offline"
    upload_cross_name = "- name: Upload genuine cross-chapter narrator identity evidence"
    assert all(workflow.count(name) == 1 for name in (
        verify_name, upload_genesis_name, cross_chapter_name, upload_cross_name
    ))

    verify_at = workflow.index(verify_name)
    upload_genesis_at = workflow.index(upload_genesis_name)
    cross_at = workflow.index(cross_chapter_name)
    upload_cross_at = workflow.index(upload_cross_name)
    assert verify_at < upload_genesis_at < cross_at < upload_cross_at

    genesis_upload = workflow[upload_genesis_at:cross_at]
    cross_step = workflow[cross_at:upload_cross_at]
    cross_upload = workflow[upload_cross_at:]
    assert "if: always()" in genesis_upload
    assert "if-no-files-found: warn" in genesis_upload
    assert "if: always() && steps.genesis1.outcome == 'success'" in cross_step
    assert "if: always()" in cross_upload
    assert "if-no-files-found: warn" in cross_upload
