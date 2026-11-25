from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from kjv_audio_generator.attribution import AttributionMap
from kjv_audio_generator.audio import ChapterAudioAssembler
from kjv_audio_generator.backend import SyntheticTestBackend
from kjv_audio_generator.models import SpeechSegment
from kjv_audio_generator.parser import parse_path
from kjv_audio_generator.voices import VoiceRegistry
from kjv_audio_generator.worker import ChapterWorker


def test_full_public_domain_kjv_genesis1_flows_through_synthetic_pipeline(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required for the Genesis 1 MP3 integration test")

    project = Path(__file__).resolve().parents[1]
    source = project / "examples" / "genesis_1_kjv_test.txt"
    document = parse_path(source)
    chapter = document.chapter("Genesis", 1)
    assert len(chapter.verses) == 31
    assert [verse.ref.verse for verse in chapter.verses] == list(range(1, 32))
    assert chapter.verses[0].text == "In the beginning God created the heaven and the earth."
    assert "sixth day" in chapter.verses[-1].text

    # Manual KJV-aware segmentation is deliberately used in this test. The source
    # text does not have quote marks, and the current importer cannot infer spoken
    # spans in unquoted King James prose.
    overrides = {
        "Genesis 1:3": [
            {"speaker_id": "narrator", "text": "And God said, "},
            {"speaker_id": "god", "text": "Let there be light: and there was light."},
        ],
        "Genesis 1:6": [
            {"speaker_id": "narrator", "text": "And God said, "},
            {"speaker_id": "god", "text": "Let there be a firmament in the midst of the waters, and let it divide the waters from the waters."},
        ],
    }
    for verse in chapter.verses:
        for item in overrides.get(verse.ref.label(), []):
            assert item["text"]
        if verse.ref.label() in overrides:
            assert "".join(item["text"] for item in overrides[verse.ref.label()]) == verse.text

    registry = VoiceRegistry.defaults()
    attribution = AttributionMap(registry, segment_overrides=overrides)
    backend = SyntheticTestBackend()
    worker = ChapterWorker(
        document,
        tmp_path,
        registry,
        attribution,
        backend,
        ChapterAudioAssembler(tmp_path, bitrate_kbps=96),
    )
    worker.start(background=False)

    assert worker.store.progress() == {"pending": 0, "running": 0, "complete": 1, "failed": 0}
    mp3 = tmp_path / "Genesis" / "Genesis_001.mp3"
    cues = tmp_path / "metadata" / "verse_timestamps" / "Genesis_001.json"
    assert mp3.is_file() and mp3.stat().st_size > 512
    payload = json.loads(cues.read_text(encoding="utf-8"))
    assert payload["book"] == "Genesis" and payload["chapter"] == 1
    assert len(payload["segments"]) == 33
    assert sum(1 for item in payload["segments"] if item["speaker_id"] == "god") == 2
    assert sum(1 for item in payload["segments"] if item["speaker_id"] == "narrator") == 31
    assert [item["reference"] for item in payload["segments"]].count("Genesis 1:31") == 1
    assert all(item["end_seconds"] > item["start_seconds"] for item in payload["segments"])
    assert backend.is_test_backend is True


def test_real_cross_chapter_voice_script_checks_persistent_narrator_profile():
    root = Path(__file__).resolve().parents[1]
    script = (root / "tools" / "qwen_cross_chapter_voice_real.py").read_text(encoding="utf-8")
    fixture = (root / "examples" / "genesis_cross_chapter_voice_test.txt").read_text(encoding="utf-8")
    source_note = (root / "examples" / "GENESIS_CROSS_CHAPTER_VOICE_TEST_SOURCE.md").read_text(encoding="utf-8")
    for token in (
        "ChapterWorker(",
        "QwenVoiceBackend(",
        "ChapterAudioAssembler(",
        "narrator_prompt_hashes",
        "narrator_fingerprint_before",
        "narrator_fingerprint_after",
        "len(preparing_events) != 1",
        'design_speakers != ["adam", "narrator"]',
        'clone_speakers != ["adam", "narrator"]',
        "GENUINE_QWEN_CROSS_CHAPTER_VOICE_IDENTITY_PASSED",
        "offline_inference",
    ):
        assert token in script
    assert "SyntheticTestBackend" not in script
    assert fixture.count("Genesis 1:1 ") == 1
    assert fixture.count("Genesis 2:23 ") == 1
    assert "not a Bible import" in source_note
    assert "Genesis.json" in source_note
