from __future__ import annotations

import json

import pytest

from kjv_audio_generator.json_io import write_json_atomic


def test_write_json_atomic_creates_parent_and_replaces_valid_utf8_json(tmp_path):
    target = tmp_path / "nested" / "metadata.json"

    write_json_atomic(target, {"greeting": "Glory, praise and peace — déjà vu"})
    first = json.loads(target.read_text(encoding="utf-8"))
    assert first == {"greeting": "Glory, praise and peace — déjà vu"}

    write_json_atomic(target, {"version": 2})
    assert json.loads(target.read_text(encoding="utf-8")) == {"version": 2}
    assert not list(target.parent.glob(".*.tmp*"))


def test_write_json_atomic_preserves_old_file_and_cleans_temp_on_replace_failure(tmp_path, monkeypatch):
    import kjv_audio_generator.json_io as json_io

    target = tmp_path / "review.json"
    original = b'{"previous": true}\n'
    target.write_bytes(original)

    def fail_replace(source, destination):
        raise OSError("injected replace failure")

    monkeypatch.setattr(json_io.os, "replace", fail_replace)
    with pytest.raises(OSError, match="injected replace failure"):
        write_json_atomic(target, {"new": True})

    assert target.read_bytes() == original
    assert not list(tmp_path.glob(".*.tmp*"))


def test_write_json_atomic_serialization_error_does_not_touch_existing_file(tmp_path):
    target = tmp_path / "review.json"
    original = b'{"previous": true}\n'
    target.write_bytes(original)

    with pytest.raises(TypeError):
        write_json_atomic(target, {"not_json": object()})

    assert target.read_bytes() == original
    assert not list(tmp_path.glob(".*.tmp*"))


def test_write_json_atomic_preserves_old_file_and_cleans_temp_on_fsync_failure(tmp_path, monkeypatch):
    import kjv_audio_generator.json_io as json_io

    target = tmp_path / "review.json"
    original = b'{"previous": true}\n'
    target.write_bytes(original)

    def fail_fsync(file_descriptor):
        raise OSError("injected fsync failure")

    monkeypatch.setattr(json_io.os, "fsync", fail_fsync)
    with pytest.raises(OSError, match="injected fsync failure"):
        write_json_atomic(target, {"new": True})

    assert target.read_bytes() == original
    assert not list(tmp_path.glob(".*.tmp*"))


def test_copy_file_atomic_replaces_existing_file_and_cleans_temp(tmp_path):
    from kjv_audio_generator.json_io import copy_file_atomic

    source = tmp_path / "rendered.mp3"
    target = tmp_path / "output" / "Genesis_001.mp3"
    source.write_bytes(b"new completed audio" * 128)
    target.parent.mkdir()
    target.write_bytes(b"old audio")

    copy_file_atomic(source, target)

    assert target.read_bytes() == source.read_bytes()
    assert not list(target.parent.glob(".*.tmp*"))


def test_copy_file_atomic_preserves_previous_file_when_replace_fails(tmp_path, monkeypatch):
    import kjv_audio_generator.json_io as json_io

    source = tmp_path / "rendered.mp3"
    target = tmp_path / "Genesis_001.mp3"
    source.write_bytes(b"new audio" * 128)
    original = b"previous audio"
    target.write_bytes(original)

    def fail_replace(staged, destination):
        raise OSError("injected MP3 replace failure")

    monkeypatch.setattr(json_io.os, "replace", fail_replace)
    with pytest.raises(OSError, match="injected MP3 replace failure"):
        json_io.copy_file_atomic(source, target)

    assert target.read_bytes() == original
    assert not list(tmp_path.glob(".*.tmp*"))


def test_atomic_output_path_commits_third_party_writer_output(tmp_path):
    from kjv_audio_generator.json_io import atomic_output_path

    target = tmp_path / "voice" / "reference.wav"
    with atomic_output_path(target) as staged:
        assert staged.parent == target.parent
        assert staged != target
        assert staged.suffix == ".wav"  # audio libraries infer format from the final extension
        staged.write_bytes(b"new reference audio")

    assert target.read_bytes() == b"new reference audio"
    assert not list(target.parent.glob(".*.tmp*"))


def test_atomic_output_path_preserves_previous_file_when_writer_fails(tmp_path):
    from kjv_audio_generator.json_io import atomic_output_path

    target = tmp_path / "prompt.pt"
    original = b"previous verified prompt"
    target.write_bytes(original)

    with pytest.raises(RuntimeError, match="writer failure"):
        with atomic_output_path(target) as staged:
            staged.write_bytes(b"partial new prompt")
            raise RuntimeError("writer failure")

    assert target.read_bytes() == original
    assert not list(tmp_path.glob(".*.tmp*"))


def test_atomic_output_path_rejects_empty_staged_output(tmp_path):
    from kjv_audio_generator.json_io import atomic_output_path

    target = tmp_path / "missing.bin"
    with pytest.raises(OSError, match="empty staged output"):
        with atomic_output_path(target):
            pass
    assert not target.exists()
    assert not list(tmp_path.glob(".*.tmp*"))


def test_atomic_output_path_uses_unique_names_for_concurrent_writers(tmp_path):
    from kjv_audio_generator.json_io import atomic_output_path

    target = tmp_path / "shared.bin"
    with atomic_output_path(target) as first:
        with atomic_output_path(target) as second:
            assert first != second
            first.write_bytes(b"first")
            second.write_bytes(b"second")
    assert target.read_bytes() == b"first"
    assert not list(tmp_path.glob(".*.tmp*"))
