from __future__ import annotations

import json

import pytest

from kjv_audio_generator.attribution import AttributionMap, SpeakerRange
from kjv_audio_generator.models import Verse, VerseRef
from kjv_audio_generator.voices import VoiceProfile, VoiceRegistry


def test_defaults_have_stable_canonical_ids_and_aliases():
    registry = VoiceRegistry.defaults()
    assert registry.resolve_alias("the Lord Jesus") == "jesus"
    assert registry.resolve_alias("Christ") == "jesus"
    assert registry.resolve_alias("the LORD") == "god"
    assert registry.get("narrator").speaker_id == "narrator"


def test_registry_save_reload_round_trip(tmp_path):
    registry = VoiceRegistry.defaults()
    path = tmp_path / "voices.json"
    registry.save(path)
    loaded = VoiceRegistry.load(path)
    assert loaded.resolve_alias("Moses the servant of the LORD") == "moses"
    assert loaded.to_dict() == registry.to_dict()


def test_duplicate_id_refused_and_voice_desc_required():
    registry = VoiceRegistry.defaults()
    with pytest.raises(ValueError, match="Duplicate speaker"):
        registry.add(VoiceProfile("narrator", "Duplicate", [], "Some voice"))
    with pytest.raises(ValueError, match="Voice description"):
        VoiceProfile("x", "X", [], "")


def test_range_assignment_defaults_to_narrator_and_is_persistent(tmp_path):
    registry = VoiceRegistry.defaults()
    mapping = AttributionMap(registry, [SpeakerRange("Genesis",1,3,7,"god",priority=10)])
    assert mapping.segments_for(Verse(VerseRef("Genesis",1,2),"Narration"))[0].speaker_id == "narrator"
    assert mapping.segments_for(Verse(VerseRef("Genesis",1,3),"God speaks"))[0].speaker_id == "god"
    path = tmp_path / "speaker_assignments.json"
    mapping.save(path)
    loaded = AttributionMap.load(path, registry)
    assert loaded.segments_for(Verse(VerseRef("Genesis",1,7),"Also God"))[0].speaker_id == "god"


def test_segment_override_supports_mixed_speakers_inside_one_verse(tmp_path):
    registry = VoiceRegistry.defaults()
    mapping = AttributionMap(registry, segment_overrides={
        "Genesis 1:3":[{"speaker_id":"narrator","text":"And God said, "}, {"speaker_id":"god","text":"Let there be light."}]
    })
    segments = mapping.segments_for(Verse(VerseRef("Genesis",1,3),"And God said, Let there be light."))
    assert [x.speaker_id for x in segments] == ["narrator", "god"]
    assert [x.text for x in segments] == ["And God said, ", "Let there be light."]


def test_unknown_speaker_assignment_is_rejected():
    registry = VoiceRegistry.defaults()
    with pytest.raises(KeyError, match="No voice profile"):
        AttributionMap(registry, [SpeakerRange("Genesis",1,1,1,"not_in_registry")])


def test_clear_speaker_seed_import_creates_reviewable_ranges_and_profiles(tmp_path):
    from kjv_audio_generator.attribution_seed import import_clear_speaker_seed

    projections = tmp_path / "Clear-Aligned-Projections.tsv"
    projections.write_text(
        "KEY\tSTART VS\tEND VS\tSPEAKER (FCBH)\tALT SPEAKER (FCBH)\n"
        "k1\tGEN 1:3\tGEN 1:4\tGod\t\n"
        "k2\tGEN 1:5\tGEN 1:5\tMoses\tGod\n"
        "k3\tGEN 2:1\tEXO 1:1\tPharaoh\t\n"
        "k4\tNOT A REF\tGEN 1:9\tEve\t\n",
        encoding="utf-8",
    )
    details = tmp_path / "character_detail.semantic_data.tsv"
    details.write_text(
        "CharacterID\tMaxSpeakers\tGender\tAge\tDivinty\n"
        "God\t1\tMale\tElder\tY\n"
        "Moses\t1\tMale\tElder\t\n"
        "Pharaoh\t1\tMale\tElder\t\n",
        encoding="utf-8",
    )
    registry = VoiceRegistry.defaults()
    attribution, report, payload = import_clear_speaker_seed(projections, details, registry)
    assert report.source_rows == 4
    assert report.suggested_ranges == 1
    assert report.uniquely_mapped_verses == 2
    assert report.ambiguous_verses == 1
    assert report.skipped_cross_chapter_rows == 1
    assert report.skipped_invalid_rows == 1
    assert report.speakers_found == 3
    assert report.profiles_created == 1  # God and Moses already have canonical profiles.
    assert attribution.segments_for(Verse(VerseRef("Genesis", 1, 3), "God said"))[0].speaker_id == "god"
    assert attribution.segments_for(Verse(VerseRef("Genesis", 1, 5), "Unclear quote"))[0].speaker_id == "unknown_speaker"
    assert "Genesis 1:5" in payload["ambiguous_verse_candidates"]
    assert "older adult" in registry.get("pharaoh").voice_description
    assert report.source_is_kjv_specific is False and report.requires_review is True

    saved = tmp_path / "speaker_assignments.json"
    attribution.save(saved)
    loaded = AttributionMap.load(saved, registry)
    assert loaded.seed_review == attribution.seed_review
    assert loaded.provenance["source_is_kjv_specific"] is False


def test_bundled_speaker_seed_loads_and_persists_on_first_run(tmp_path):
    from kjv_audio_generator.attribution_seed import load_or_seed_attribution

    runtime = tmp_path / "bundle"
    source = runtime / "data" / "speaker-attribution"
    source.mkdir(parents=True)
    (source / "Clear-Aligned-Projections.tsv").write_text(
        "KEY\tSTART VS\tEND VS\tSPEAKER (FCBH)\tALT SPEAKER (FCBH)\n"
        "k1\tGEN 1:3\tGEN 1:4\tGod\t\n",
        encoding="utf-8",
    )
    (source / "character_detail.semantic_data.tsv").write_text(
        "CharacterID\tGender\tAge\tDivinty\nGod\tMale\tElder\tY\n",
        encoding="utf-8",
    )
    output = tmp_path / "audio"
    registry = VoiceRegistry.defaults()
    attribution = load_or_seed_attribution(output, runtime, registry)
    assert attribution.segments_for(Verse(VerseRef("Genesis", 1, 3), "And God said"))[0].speaker_id == "god"
    assert (output / "metadata" / "speaker_assignments.json").is_file()
    assert (output / "metadata" / "voice_registry.json").is_file()
    assert (output / "metadata" / "speaker_seed_review.json").is_file()


def test_attribution_splits_explicit_quoted_dialogue_from_narration():
    from kjv_audio_generator.attribution import AttributionMap, SpeakerRange
    from kjv_audio_generator.models import Verse, VerseRef
    from kjv_audio_generator.voices import VoiceRegistry

    registry = VoiceRegistry.defaults()
    attribution = AttributionMap(
        registry, [SpeakerRange("Genesis", 3, 4, 4, "god")]
    )
    verse = Verse(VerseRef("Genesis", 3, 4), 'And the serpent said, “Ye shall not surely die.” And the woman listened.')
    segments = attribution.segments_for(verse)

    assert [segment.speaker_id for segment in segments] == ["narrator", "god", "narrator"]
    assert "And the serpent said," in segments[0].text
    assert "Ye shall not surely die." in segments[1].text
    assert "And the woman listened." in segments[2].text
    assert "".join(segment.text for segment in segments) == verse.text


def test_attribution_keeps_single_speaker_for_unmarked_verse():
    from kjv_audio_generator.attribution import AttributionMap, SpeakerRange
    from kjv_audio_generator.models import Verse, VerseRef
    from kjv_audio_generator.voices import VoiceRegistry

    registry = VoiceRegistry.defaults()
    attribution = AttributionMap(
        registry, [SpeakerRange("Genesis", 3, 4, 4, "god")]
    )
    verse = Verse(VerseRef("Genesis", 3, 4), "And the serpent said unto the woman, Ye shall not surely die.")
    segments = attribution.segments_for(verse)

    assert len(segments) == 1
    assert segments[0].speaker_id == "god"
    assert segments[0].text == verse.text


def test_stale_manual_segments_are_rejected_when_imported_verse_changes():
    registry = VoiceRegistry.defaults()
    attribution = AttributionMap(registry, segment_overrides={
        "Genesis 1:3": [
            {"speaker_id": "narrator", "text": "And God said, "},
            {"speaker_id": "god", "text": "Let there be light."},
        ]
    })
    edited_verse = Verse(VerseRef("Genesis", 1, 3), "And God said, Let there be light and more text.")
    with pytest.raises(ValueError, match="no longer match"):
        attribution.segments_for(edited_verse)


def test_quote_splitting_preserves_whitespace_around_quote_spans():
    registry = VoiceRegistry.defaults()
    attribution = AttributionMap(registry, [SpeakerRange("Genesis", 3, 4, 4, "god")])
    verse = Verse(VerseRef("Genesis", 3, 4), '  And the serpent said, “Ye shall not surely die.”  ')
    segments = attribution.segments_for(verse)
    assert "".join(item.text for item in segments) == verse.text
    assert [item.speaker_id for item in segments] == ["narrator", "god"]
    assert segments[0].text == "  And the serpent said, "
    assert segments[-1].text == "“Ye shall not surely die.”  "
    assert all(item.text.strip() for item in segments)


def test_seed_normalizes_book_specific_narrators_and_jesus_child_to_canonical_profiles(tmp_path):
    from kjv_audio_generator.attribution_seed import import_clear_speaker_seed

    projections = tmp_path / "Clear-Aligned-Projections.tsv"
    projections.write_text(
        "KEY\tSTART VS\tEND VS\tSPEAKER (FCBH)\tALT SPEAKER (FCBH)\n"
        "k1\tGEN 1:3\tGEN 1:3\tnarrator-GEN\t\n"
        "k2\tGEN 1:4\tGEN 1:4\tnarrator-JHN\t\n"
        "k3\tGEN 1:5\tGEN 1:5\tJesus (child)\t\n"
        "k4\tGEN 1:6\tGEN 1:6\tJesus\t\n",
        encoding="utf-8",
    )
    registry = VoiceRegistry.defaults()
    attribution, report, _review = import_clear_speaker_seed(projections, None, registry)
    assert report.profiles_created == 0
    assert "narrator_gen" not in registry.profiles
    assert "narrator_jhn" not in registry.profiles
    assert "jesus_child" not in registry.profiles
    assert [(r.start_verse, r.end_verse, r.speaker_id) for r in attribution.ranges] == [
        (3, 4, "narrator"), (5, 6, "jesus")
    ]


def test_compound_speaker_label_is_left_unknown_and_flagged_for_review(tmp_path):
    from kjv_audio_generator.attribution_seed import import_clear_speaker_seed

    projections = tmp_path / "Clear-Aligned-Projections.tsv"
    projections.write_text(
        "KEY\tSTART VS\tEND VS\tSPEAKER (FCBH)\tALT SPEAKER (FCBH)\n"
        "k1\tGEN 1:7\tGEN 1:7\tGod/Jeremiah\t\n",
        encoding="utf-8",
    )
    registry = VoiceRegistry.defaults()
    attribution, report, review = import_clear_speaker_seed(projections, None, registry)
    assert report.profiles_created == 0
    assert "god_jeremiah" not in registry.profiles
    assert attribution.seed_review["Genesis 1:7"] == ["unknown_speaker"]
    assert attribution.segments_for(Verse(VerseRef("Genesis", 1, 7), "An ambiguous quotation."))[0].speaker_id == "unknown_speaker"
    assert "Genesis 1:7" in review["ambiguous_verse_candidates"]
