from __future__ import annotations

from pathlib import Path

import pytest

from tools.verify_chapter_transcript import (
    assess_chapter_transcript,
    validate_chapter_cues,
)


def test_genesis_one_cues_reconstruct_all_31_source_verses_exactly():
    root = Path(__file__).resolve().parents[1]
    source = root / "examples" / "genesis_1_kjv_test.txt"
    segments = []
    document_text = source.read_text(encoding="utf-8")
    from kjv_audio_generator.parser import parse_path
    chapter = parse_path(source).chapter("Genesis", 1)
    for verse in chapter.verses:
        segments.append({
            "reference": verse.ref.label(),
            "text": verse.text,
            "start_seconds": len(segments) * 1.0,
            "end_seconds": len(segments) * 1.0 + 0.5,
        })
    cue = root / "tests" / "_temp_genesis1_cues_fixture.json"
    import json
    cue.write_text(json.dumps({
        "book": "Genesis",
        "chapter": 1,
        "duration_seconds": 31.5,
        "segments": segments,
    }), encoding="utf-8")
    try:
        result = validate_chapter_cues(source, cue)
    finally:
        cue.unlink(missing_ok=True)
    assert result["source_verse_count"] == 31
    assert result["unique_verse_count"] == 31
    assert result["cue_segment_count"] == 31
    assert result["required_trailing_phrase"].endswith("sixth day")


def test_genesis_one_cue_validation_rejects_missing_verse(tmp_path):
    root = Path(__file__).resolve().parents[1]
    source = root / "examples" / "genesis_1_kjv_test.txt"
    from kjv_audio_generator.parser import parse_path
    chapter = parse_path(source).chapter("Genesis", 1)
    segments = [
        {
            "reference": verse.ref.label(),
            "text": verse.text,
            "start_seconds": index * 1.0,
            "end_seconds": index * 1.0 + 0.5,
        }
        for index, verse in enumerate(chapter.verses[:-1])
    ]
    cue = tmp_path / "missing.json"
    import json
    cue.write_text(json.dumps({"book": "Genesis", "chapter": 1, "segments": segments}), encoding="utf-8")
    with pytest.raises(ValueError, match="coverage/order"):
        validate_chapter_cues(source, cue)


def test_genesis_one_cue_validation_accepts_split_verse_segments():
    root = Path(__file__).resolve().parents[1]
    source = root / "examples" / "genesis_1_kjv_test.txt"
    from kjv_audio_generator.parser import parse_path
    chapter = parse_path(source).chapter("Genesis", 1)
    segments = []
    for verse in chapter.verses:
        if verse.ref.label() == "Genesis 1:3":
            parts = ["And God said, ", "Let there be light: and there was light."]
        else:
            parts = [verse.text]
        for part in parts:
            index = len(segments)
            segments.append({
                "reference": verse.ref.label(),
                "text": part,
                "start_seconds": index * 0.5,
                "end_seconds": index * 0.5 + 0.25,
            })
    cue = root / "tests" / "_temp_split_genesis1_cues_fixture.json"
    import json
    cue.write_text(json.dumps({"book": "Genesis", "chapter": 1, "segments": segments}), encoding="utf-8")
    try:
        result = validate_chapter_cues(source, cue)
    finally:
        cue.unlink(missing_ok=True)
    assert result["cue_segment_count"] == 32
    assert result["source_verse_count"] == 31


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
