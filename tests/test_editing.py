from __future__ import annotations

import pytest

from kjv_audio_generator.editing import format_segments_for_editor, parse_segments_from_editor
from kjv_audio_generator.models import VerseRef
from kjv_audio_generator.voices import VoiceRegistry


def test_editor_round_trip_exact_two_speaker_verse():
    registry = VoiceRegistry.defaults()
    verse = VerseRef("Genesis", 1, 3)
    original = "And God said, Let there be light: and there was light."
    content = format_segments_for_editor([
        ("narrator", "And God said, "),
        ("god", "Let there be light: and there was light."),
    ])
    parsed = parse_segments_from_editor(content, verse_ref=verse, original_text=original, registry=registry)
    assert parsed == [
        {"speaker_id": "narrator", "text": "And God said, "},
        {"speaker_id": "god", "text": "Let there be light: and there was light."},
    ]
    assert "".join(item["text"] for item in parsed) == original


def test_editor_rejects_unknown_speaker():
    registry = VoiceRegistry.defaults()
    verse = VerseRef("Genesis", 1, 1)
    with pytest.raises(ValueError, match="unknown speaker"):
        parse_segments_from_editor("adam\tIn the beginning.", verse_ref=verse,
                                   original_text="In the beginning.", registry=registry)


def test_editor_rejects_text_changes_and_omissions():
    registry = VoiceRegistry.defaults()
    verse = VerseRef("Genesis", 1, 1)
    with pytest.raises(ValueError, match="exactly"):
        parse_segments_from_editor("narrator\tIn beginning.", verse_ref=verse,
                                   original_text="In the beginning.", registry=registry)


def test_editor_requires_tab_and_nonempty_segment():
    registry = VoiceRegistry.defaults()
    verse = VerseRef("Genesis", 1, 1)
    with pytest.raises(ValueError, match="TAB|tab"):
        parse_segments_from_editor("narrator In the beginning.", verse_ref=verse,
                                   original_text="In the beginning.", registry=registry)
    with pytest.raises(ValueError, match="empty text"):
        parse_segments_from_editor("narrator\t", verse_ref=verse,
                                   original_text="In the beginning.", registry=registry)


def test_editor_requires_at_least_one_segment():
    registry = VoiceRegistry.defaults()
    verse = VerseRef("Genesis", 1, 1)
    with pytest.raises(ValueError, match="No speech segments"):
        parse_segments_from_editor("", verse_ref=verse,
                                   original_text="In the beginning.", registry=registry)
