from __future__ import annotations

import sys
import types
import ctypes

import numpy as np
import pytest
import torch

from kjv_audio_generator.backend import QwenSettings, QwenVoiceBackend
from kjv_audio_generator.voices import VoiceProfile


def _truncate_sparse_file(target, size):
    """Create a large logical weight file without reserving its full disk size."""
    with target.open("w+b") as handle:
        if sys.platform == "win32":
            # Mark the NTFS file sparse before extending it. SetEndOfFile /
            # ordinary zero writes can still allocate physical clusters in an
            # already-sparse file, so release the newly zeroed range explicitly
            # with FSCTL_SET_ZERO_DATA after setting the logical file length.
            import msvcrt
            from ctypes import wintypes

            fsctl_set_sparse = 0x000900C4  # FSCTL_SET_SPARSE from winioctl.h
            fsctl_set_zero_data = 0x000980C8  # FSCTL_SET_ZERO_DATA from winioctl.h
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            device_io_control = kernel32.DeviceIoControl
            device_io_control.argtypes = [
                wintypes.HANDLE,
                wintypes.DWORD,
                ctypes.c_void_p,
                wintypes.DWORD,
                ctypes.c_void_p,
                wintypes.DWORD,
                ctypes.POINTER(wintypes.DWORD),
                ctypes.c_void_p,
            ]
            device_io_control.restype = wintypes.BOOL
            bytes_returned = wintypes.DWORD(0)
            handle_value = wintypes.HANDLE(msvcrt.get_osfhandle(handle.fileno()))
            marked_sparse = device_io_control(
                handle_value,
                fsctl_set_sparse,
                None,
                0,
                None,
                0,
                ctypes.byref(bytes_returned),
                None,
            )
            if not marked_sparse:
                raise ctypes.WinError(ctypes.get_last_error())
            handle.truncate(size)
            handle.flush()

            class FileZeroDataInformation(ctypes.Structure):
                _fields_ = [
                    ("FileOffset", ctypes.c_longlong),
                    ("BeyondFinalZero", ctypes.c_longlong),
                ]

            zero_range = FileZeroDataInformation(0, size)
            deallocated = device_io_control(
                handle_value,
                fsctl_set_zero_data,
                ctypes.byref(zero_range),
                ctypes.sizeof(zero_range),
                None,
                0,
                ctypes.byref(bytes_returned),
                None,
            )
            if not deallocated:
                raise ctypes.WinError(ctypes.get_last_error())
        else:
            handle.truncate(size)


def make_fake_model_folder(path):
    """Build the file layout required by the official Qwen3-TTS model cards."""
    files = (
        "generation_config.json",
        "tokenizer_config.json",
        "vocab.json",
        "merges.txt",
        "preprocessor_config.json",
        "speech_tokenizer/configuration.json",
        "speech_tokenizer/preprocessor_config.json",
    )
    path.mkdir(parents=True, exist_ok=True)
    model_type = "base" if "base" in path.name.casefold() else "voice_design"
    (path / "config.json").write_text(
        '{"model_type":"qwen3_tts","tokenizer_type":"qwen3_tts_tokenizer_12hz",'
        f'"tts_model_type":"{model_type}"}}', encoding="utf-8"
    )
    (path / "speech_tokenizer" / "config.json").parent.mkdir(parents=True, exist_ok=True)
    (path / "speech_tokenizer" / "config.json").write_text(
        '{"model_type":"qwen3_tts_tokenizer_12hz"}', encoding="utf-8"
    )
    for relative in files:
        target = path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if relative == "generation_config.json" or relative.endswith(".json"):
            target.write_text("{}", encoding="utf-8")
        else:
            target.write_bytes(b"test-placeholder")
    # Mark fake model weights sparse on Windows before extending them;
    # Linux filesystems already make truncate() sparse by default.
    for relative, minimum in (("model.safetensors", 3_500_000_000),
                              ("speech_tokenizer/model.safetensors", 650_000_000)):
        target = path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        _truncate_sparse_file(target, minimum)
    return path


class FakeQwenModel:
    calls = []
    def __init__(self, model_path): self.model_path = model_path
    @classmethod
    def from_pretrained(cls, path, **kwargs):
        cls.calls.append(("load",path,kwargs))
        return cls(path)
    def generate_voice_design(self, text, instruct, language):
        self.calls.append(("design",instruct,text,language))
        t = np.arange(2400,dtype=np.float32)/24000
        return [0.04*np.sin(2*np.pi*180*t)],24000
    def create_voice_clone_prompt(self, ref_audio, ref_text, x_vector_only_mode):
        from types import SimpleNamespace
        self.calls.append(("prompt",ref_audio,ref_text,x_vector_only_mode))
        return [SimpleNamespace(
            ref_code=torch.tensor([[1, 2, 3]], dtype=torch.int64),
            ref_spk_embedding=torch.tensor([0.1, 0.2, 0.3], dtype=torch.float32),
            x_vector_only_mode=bool(x_vector_only_mode),
            icl_mode=not bool(x_vector_only_mode),
            ref_text=ref_text,
        )]
    def generate_voice_clone(self, text, language, voice_clone_prompt, non_streaming_mode):
        # Match qwen-tts 0.1.1's public wrapper path: passing a list of prompt
        # items preserves each ref_text so it can build ref_ids for ICL mode.
        assert isinstance(voice_clone_prompt, list)
        assert voice_clone_prompt
        assert all(hasattr(item, "ref_spk_embedding") for item in voice_clone_prompt)
        assert all(hasattr(item, "ref_text") and item.ref_text for item in voice_clone_prompt)
        self.calls.append(("clone",text,voice_clone_prompt,non_streaming_mode))
        t = np.arange(4000,dtype=np.float32)/24000
        return [0.05*np.sin(2*np.pi*210*t)],24000


def test_qwen_design_to_clone_prompt_is_saved_and_reused(tmp_path, monkeypatch):
    FakeQwenModel.calls = []
    fake_module = types.ModuleType("qwen_tts")
    fake_module.Qwen3TTSModel = FakeQwenModel
    monkeypatch.setitem(sys.modules,"qwen_tts",fake_module)
    design = tmp_path/"models"/"design"; base = tmp_path/"models"/"base"
    design.mkdir(parents=True); base.mkdir(parents=True)
    make_fake_model_folder(design)
    make_fake_model_folder(base)
    profiles = [
        VoiceProfile("narrator","Narrator",[],"Clear warm narrator"),
        VoiceProfile("moses","Moses",[],"Mature weathered voice"),
    ]
    backend = QwenVoiceBackend(QwenSettings(design,base,"cpu"),tmp_path/"assets")
    backend.prepare_profiles(profiles)
    assert (tmp_path/"assets"/"narrator.reference.wav").is_file()
    assert (tmp_path/"assets"/"narrator.prompt.pt").is_file()
    assert (tmp_path/"assets"/"moses.prompt.pt").is_file()
    assert FakeQwenModel.calls.count(("load",str(design),{"device_map":"cpu","dtype":"auto","local_files_only":True})) == 1
    assert sum(1 for c in FakeQwenModel.calls if c[0]=="prompt") == 2
    first,_ = backend.synthesize("A line by Moses",profiles[1])
    second,_ = backend.synthesize("Another line by Moses",profiles[1])
    assert first.size and second.size
    assert sum(1 for c in FakeQwenModel.calls if c[0]=="prompt") == 2
    assert isinstance(backend._prompt_cache["moses"], dict)
    assert len(backend._prompt_cache["moses"]["ref_spk_embedding"]) == 1
    clone_calls = [c for c in FakeQwenModel.calls if c[0] == "clone"]
    assert len(clone_calls) == 2
    assert all(call[2][0].ref_text == profiles[1].reference_text for call in clone_calls)
    assert all(call[2][0].icl_mode and call[2][0].ref_code is not None for call in clone_calls)


def test_qwen_backend_fails_closed_when_model_folder_missing(tmp_path):
    import pytest
    from kjv_audio_generator.backend import QwenRuntimeUnavailable
    backend = QwenVoiceBackend(QwenSettings(tmp_path/"missing_design",tmp_path/"missing_base"),tmp_path/"profiles")
    with pytest.raises(QwenRuntimeUnavailable,match="Base model folder is missing"):
        backend.prepare_profiles([VoiceProfile("narrator","Narrator",[],"Clear")])


def test_saved_voice_prompt_reloads_without_redesigning_reference(tmp_path, monkeypatch):
    FakeQwenModel.calls = []
    fake_module = types.ModuleType("qwen_tts")
    fake_module.Qwen3TTSModel = FakeQwenModel
    monkeypatch.setitem(sys.modules, "qwen_tts", fake_module)
    design = tmp_path / "models" / "design"
    base = tmp_path / "models" / "base"
    design.mkdir(parents=True); base.mkdir(parents=True)
    make_fake_model_folder(design)
    make_fake_model_folder(base)
    profile = VoiceProfile("moses", "Moses", [], "Mature weathered voice")
    first = QwenVoiceBackend(QwenSettings(design, base, "cpu"), tmp_path / "assets")
    first.prepare_profiles([profile])
    first_prompt_calls = sum(1 for call in FakeQwenModel.calls if call[0] == "prompt")
    assert first_prompt_calls == 1

    restarted = QwenVoiceBackend(QwenSettings(design, base, "cpu"), tmp_path / "assets")
    progress = []
    restarted.prepare_profiles([profile], progress_callback=lambda *args: progress.append(args))
    assert any(item[0] == "cached" for item in progress)
    assert sum(1 for call in FakeQwenModel.calls if call[0] == "design") == 1
    assert sum(1 for call in FakeQwenModel.calls if call[0] == "prompt") == 1
    samples, rate = restarted.synthesize("Moses speaks again.", profile)
    assert samples.size and rate == 24000


def test_changed_voice_description_invalidates_saved_profile_assets(tmp_path, monkeypatch):
    FakeQwenModel.calls = []
    fake_module = types.ModuleType("qwen_tts")
    fake_module.Qwen3TTSModel = FakeQwenModel
    monkeypatch.setitem(sys.modules, "qwen_tts", fake_module)
    design = tmp_path / "models" / "design"
    base = tmp_path / "models" / "base"
    design.mkdir(parents=True); base.mkdir(parents=True)
    make_fake_model_folder(design)
    make_fake_model_folder(base)
    profile = VoiceProfile("moses", "Moses", [], "Mature weathered voice")
    first = QwenVoiceBackend(QwenSettings(design, base, "cpu"), tmp_path / "assets")
    first.prepare_profiles([profile])
    profile.voice_description = "A brighter, lighter, more youthful male voice"

    revised = QwenVoiceBackend(QwenSettings(design, base, "cpu"), tmp_path / "assets")
    revised.prepare_profiles([profile])
    assert sum(1 for call in FakeQwenModel.calls if call[0] == "design") == 2
    assert sum(1 for call in FakeQwenModel.calls if call[0] == "prompt") == 2
    assert profile.status == "prepared"


def test_qwen_backend_bounds_prompt_memory_for_large_character_cast(tmp_path, monkeypatch):
    FakeQwenModel.calls = []
    fake_module = types.ModuleType("qwen_tts")
    fake_module.Qwen3TTSModel = FakeQwenModel
    monkeypatch.setitem(sys.modules, "qwen_tts", fake_module)
    design = tmp_path / "models" / "design"
    base = tmp_path / "models" / "base"
    design.mkdir(parents=True); base.mkdir(parents=True)
    make_fake_model_folder(design)
    make_fake_model_folder(base)
    profiles = [VoiceProfile(f"character_{i}", f"Character {i}", [], f"Voice {i}") for i in range(12)]
    backend = QwenVoiceBackend(QwenSettings(design, base, "cpu"), tmp_path / "assets")
    backend.prepare_profiles(profiles)
    assert all((tmp_path / "assets" / f"character_{i}.prompt.pt").is_file() for i in range(12))
    assert len(backend._prompt_cache) <= backend._prompt_cache_limit == 8
    backend.synthesize("A line from character 0", profiles[0])
    assert len(backend._prompt_cache) <= 8
    assert "character_0" in backend._prompt_cache


def test_qwen_model_preflight_rejects_missing_nested_speech_tokenizer(tmp_path):
    import pytest
    from kjv_audio_generator.backend import QwenRuntimeUnavailable

    model = tmp_path / "partial_model"
    model.mkdir()
    (model / "README.md").write_text("A non-empty folder is not a usable model")
    with pytest.raises(QwenRuntimeUnavailable, match="model folder is incomplete"):
        QwenVoiceBackend._require_directory(model, "Base")

    make_fake_model_folder(model)
    (model / "config.json").write_text(
        '{"model_type":"qwen3_tts","tokenizer_type":"qwen3_tts_tokenizer_12hz","tts_model_type":"base"}',
        encoding="utf-8",
    )
    QwenVoiceBackend._require_directory(model, "Base")


def test_qwen_preflight_rejects_model_weight_placeholders(tmp_path):
    import pytest
    from kjv_audio_generator.backend import QwenRuntimeUnavailable

    model = tmp_path / "small_fake_model"
    make_fake_model_folder(model)
    (model / "model.safetensors").write_bytes(b"placeholder")
    with pytest.raises(QwenRuntimeUnavailable, match="too small to be the official 1.7B"):
        QwenVoiceBackend._require_directory(model, "VoiceDesign")


def test_qwen_preflight_rejects_wrong_model_type(tmp_path):
    import pytest
    from kjv_audio_generator.backend import QwenRuntimeUnavailable

    model = tmp_path / "wrong_type_model"
    make_fake_model_folder(model)
    (model / "config.json").write_text(
        '{"model_type":"qwen3_tts","tokenizer_type":"qwen3_tts_tokenizer_12hz","tts_model_type":"base"}',
        encoding="utf-8",
    )
    with pytest.raises(QwenRuntimeUnavailable, match="wrong Qwen TTS model type"):
        QwenVoiceBackend._require_directory(model, "VoiceDesign")


def test_missing_external_reference_audio_fails_instead_of_silently_redesigning_voice(tmp_path, monkeypatch):
    import pytest
    from kjv_audio_generator.backend import QwenRuntimeUnavailable

    FakeQwenModel.calls = []
    fake_module = types.ModuleType("qwen_tts")
    fake_module.Qwen3TTSModel = FakeQwenModel
    monkeypatch.setitem(sys.modules, "qwen_tts", fake_module)
    design = tmp_path / "models" / "design"
    base = tmp_path / "models" / "base"
    design.mkdir(parents=True); base.mkdir(parents=True)
    make_fake_model_folder(design)
    make_fake_model_folder(base)
    profile = VoiceProfile(
        "moses", "Moses", [], "Mature weathered voice",
        reference_audio=str(tmp_path / "missing-reference.wav"),
    )
    backend = QwenVoiceBackend(QwenSettings(design, base, "cpu"), tmp_path / "assets")
    with pytest.raises(QwenRuntimeUnavailable, match="Reference audio for moses is missing"):
        backend.prepare_profiles([profile])
    assert not any(call[0] == "design" for call in FakeQwenModel.calls)
    assert not (tmp_path / "assets" / "moses.reference.wav").exists()


def test_prepared_external_reference_prompt_remains_portable_when_source_wav_is_missing(tmp_path, monkeypatch):
    FakeQwenModel.calls = []
    fake_module = types.ModuleType("qwen_tts")
    fake_module.Qwen3TTSModel = FakeQwenModel
    monkeypatch.setitem(sys.modules, "qwen_tts", fake_module)
    design = tmp_path / "models" / "design"
    base = tmp_path / "models" / "base"
    design.mkdir(parents=True); base.mkdir(parents=True)
    make_fake_model_folder(design)
    make_fake_model_folder(base)
    external = tmp_path / "source-reference.wav"
    external.write_bytes(b"fake reference audio for adapter contract")
    profile = VoiceProfile("moses", "Moses", [], "Mature weathered voice", reference_text="Speak clearly.", reference_audio=str(external))

    first = QwenVoiceBackend(QwenSettings(design, base, "cpu"), tmp_path / "project" / "voice_assets")
    first.prepare_profiles([profile])
    assert (tmp_path / "project" / "voice_assets" / "moses.prompt.pt").is_file()
    external.unlink()

    # A portable output directory can reuse its stored prompt even if the original
    # source recording was on another drive that is no longer mounted.
    restarted = QwenVoiceBackend(QwenSettings(design, base, "cpu"), tmp_path / "project" / "voice_assets")
    progress = []
    restarted.prepare_profiles([profile], progress_callback=lambda *args: progress.append(args))
    assert any(item[0] == "cached" for item in progress)
    assert sum(1 for call in FakeQwenModel.calls if call[0] == "prompt") == 1
    assert sum(1 for call in FakeQwenModel.calls if call[0] == "design") == 0
    samples, rate = restarted.synthesize("Moses speaks from the portable prompt.", profile)
    assert samples.size and rate == 24000


def test_missing_external_reference_with_tampered_prompt_fails_closed(tmp_path, monkeypatch):
    import pytest
    from kjv_audio_generator.backend import QwenRuntimeUnavailable

    FakeQwenModel.calls = []
    fake_module = types.ModuleType("qwen_tts")
    fake_module.Qwen3TTSModel = FakeQwenModel
    monkeypatch.setitem(sys.modules, "qwen_tts", fake_module)
    design = tmp_path / "models" / "design"
    base = tmp_path / "models" / "base"
    design.mkdir(parents=True); base.mkdir(parents=True)
    make_fake_model_folder(design)
    make_fake_model_folder(base)
    external = tmp_path / "source-reference.wav"
    external.write_bytes(b"fake reference audio")
    profile = VoiceProfile("moses", "Moses", [], "Mature voice", reference_text="Speak.", reference_audio=str(external))
    backend = QwenVoiceBackend(QwenSettings(design, base, "cpu"), tmp_path / "assets")
    backend.prepare_profiles([profile])
    external.unlink()
    prompt_path = tmp_path / "assets" / "moses.prompt.pt"
    prompt_path.write_bytes(prompt_path.read_bytes() + b"tampered")
    restarted = QwenVoiceBackend(QwenSettings(design, base, "cpu"), tmp_path / "assets")
    with pytest.raises(QwenRuntimeUnavailable, match="verified saved voice prompt is unavailable"):
        restarted.prepare_profiles([profile])


def test_multiple_profiles_keep_their_own_external_reference_paths(tmp_path, monkeypatch):
    """Each prepared prompt must persist the reference belonging to that profile."""
    import json

    FakeQwenModel.calls = []
    fake_module = types.ModuleType("qwen_tts")
    fake_module.Qwen3TTSModel = FakeQwenModel
    monkeypatch.setitem(sys.modules, "qwen_tts", fake_module)
    design = tmp_path / "models" / "design"
    base = tmp_path / "models" / "base"
    design.mkdir(parents=True); base.mkdir(parents=True)
    make_fake_model_folder(design)
    make_fake_model_folder(base)

    reference_a = tmp_path / "Moses-reference.wav"
    reference_b = tmp_path / "Jesus-reference.wav"
    reference_a.write_bytes(b"distinct external voice reference A")
    reference_b.write_bytes(b"distinct external voice reference B")
    profiles = [
        VoiceProfile("moses", "Moses", [], "Weathered mature male voice", "Moses says.", str(reference_a)),
        VoiceProfile("narrator", "Narrator", [], "Warm clear narrator voice"),
        VoiceProfile("jesus", "Jesus", [], "Warm compassionate voice", "Jesus says.", str(reference_b)),
    ]
    assets = tmp_path / "project" / "voice_assets"
    first = QwenVoiceBackend(QwenSettings(design, base, "cpu"), assets)
    first.prepare_profiles(profiles)

    expected = {
        "moses": str(reference_a),
        "narrator": None,
        "jesus": str(reference_b),
    }
    for speaker_id, reference_path in expected.items():
        meta = json.loads((assets / f"{speaker_id}.prompt.prompt.json").read_text(encoding="utf-8"))
        assert meta["reference_audio_path"] == reference_path

    # Reopen the portable project with both external source paths unavailable.
    reference_a.unlink()
    reference_b.unlink()
    restarted = QwenVoiceBackend(QwenSettings(design, base, "cpu"), assets)
    progress = []
    restarted.prepare_profiles(profiles, progress_callback=lambda *args: progress.append(args))
    cached_ids = {item[3] for item in progress if item[0] == "cached"}
    assert cached_ids == {"moses", "narrator", "jesus"}
    assert sum(call[0] == "prompt" for call in FakeQwenModel.calls) == 3
    assert sum(call[0] == "design" for call in FakeQwenModel.calls) == 1
    for profile in profiles:
        audio, sample_rate = restarted.synthesize("A stable voice test line.", profile)
        assert audio.size and sample_rate == 24000


def test_generated_voice_prompt_survives_project_folder_relocation(tmp_path, monkeypatch):
    import json
    import shutil
    from pathlib import Path

    FakeQwenModel.calls = []
    fake_module = types.ModuleType("qwen_tts")
    fake_module.Qwen3TTSModel = FakeQwenModel
    monkeypatch.setitem(sys.modules, "qwen_tts", fake_module)
    design = tmp_path / "models" / "design"
    base = tmp_path / "models" / "base"
    design.mkdir(parents=True); base.mkdir(parents=True)
    make_fake_model_folder(design)
    make_fake_model_folder(base)

    profile = VoiceProfile("moses", "Moses", [], "Mature weathered voice")
    original_assets = tmp_path / "usb-drive-old" / "voice_assets"
    original = QwenVoiceBackend(QwenSettings(design, base, "cpu"), original_assets)
    original.prepare_profiles([profile])
    assert profile.reference_audio == str(original_assets / "moses.reference.wav")
    prompt = original_assets / "moses.prompt.pt"
    prompt_meta = prompt.with_suffix(".prompt.json")
    saved_signature = json.loads(prompt_meta.read_text(encoding="utf-8"))["signature"]

    # Simulate copying the project folder to another drive. The prompt and its
    # metadata move, while the registry retains the old absolute generated WAV path.
    moved_assets = tmp_path / "usb-drive-new" / "voice_assets"
    moved_assets.mkdir(parents=True)
    shutil.copy2(prompt, moved_assets / prompt.name)
    shutil.copy2(prompt_meta, (moved_assets / prompt.name).with_suffix(".prompt.json"))
    Path(profile.reference_audio).unlink()

    moved = QwenVoiceBackend(QwenSettings(design, base, "cpu"), moved_assets)
    assert moved.profile_fingerprint(profile) == saved_signature
    progress = []
    moved.prepare_profiles([profile], progress_callback=lambda *args: progress.append(args))
    assert any(item[0] == "cached" for item in progress)
    assert sum(1 for call in FakeQwenModel.calls if call[0] == "design") == 1
    assert sum(1 for call in FakeQwenModel.calls if call[0] == "prompt") == 1
    audio, rate = moved.synthesize("Moses speaks after the project folder moved.", profile)
    assert audio.size and rate == 24000


def test_qwen_generation_fingerprint_uses_pinned_model_snapshot_manifest(tmp_path):
    import hashlib
    import json
    import pytest
    from kjv_audio_generator.backend import QwenRuntimeUnavailable

    design = tmp_path / "models" / "Qwen3-TTS-12Hz-1.7B-VoiceDesign"
    base = tmp_path / "models" / "Qwen3-TTS-12Hz-1.7B-Base"
    design.mkdir(parents=True); base.mkdir(parents=True)
    rows = []
    specs = [
        (design, "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", "5ecdb67327fd37bb2e042aab12ff7391903235d3", "voice_design"),
        (base, "Qwen/Qwen3-TTS-12Hz-1.7B-Base", "fd4b254389122332181a7c3db7f27e918eec64e3", "base"),
    ]
    for folder, repo, revision, kind in specs:
        (folder / "config.json").write_text(json.dumps({"model_type": "qwen3_tts", "tts_model_type": kind}), encoding="utf-8")
        (folder / "speech_tokenizer").mkdir()
        (folder / "speech_tokenizer" / "config.json").write_text('{"model_type":"qwen3_tts_tokenizer_12hz"}', encoding="utf-8")
        (folder / "model.safetensors").write_bytes((kind + " main weights").encode())
        (folder / "speech_tokenizer" / "model.safetensors").write_bytes((kind + " tokenizer weights").encode())
        rows.append({
            "repo": repo,
            "revision": revision,
            "folder": folder.name,
            "kind": kind,
            "config_sha256": hashlib.sha256((folder / "config.json").read_bytes()).hexdigest(),
            "speech_tokenizer_config_sha256": hashlib.sha256((folder / "speech_tokenizer" / "config.json").read_bytes()).hexdigest(),
            "model_bytes": (folder / "model.safetensors").stat().st_size,
            "speech_tokenizer_bytes": (folder / "speech_tokenizer" / "model.safetensors").stat().st_size,
        })
    manifest_path = design.parent / "KJV_QWEN_ASSET_MANIFEST.json"
    manifest = {
        "schema_version": 1,
        "models": rows,
        "speaker_seed": {"repo": "Clear-Bible/speaker-quotations", "revision": "b09e308a3a1aafdb7d6c75baf0fe2a31d61601da"},
        "qwen_package": "qwen-tts==0.1.1",
        "transformers": "transformers==4.57.3",
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    backend = QwenVoiceBackend(QwenSettings(design, base, "cpu"), tmp_path / "assets")
    fingerprint_a = backend.generation_fingerprint()

    # A manifest edit that doesn't match the actual model files must fail closed.
    manifest["models"][1]["model_bytes"] += 1
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(QwenRuntimeUnavailable, match="manifest mismatch"):
        backend.generation_fingerprint()

    # After a correct manifest refresh, replacing the actual model config changes
    # the fingerprint; an unapproved model snapshot revision is rejected.
    manifest["models"][1]["model_bytes"] -= 1
    (base / "config.json").write_text(json.dumps({"model_type": "qwen3_tts", "tts_model_type": "base", "test_revision": 2}), encoding="utf-8")
    manifest["models"][1]["config_sha256"] = hashlib.sha256((base / "config.json").read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    fingerprint_b = backend.generation_fingerprint()
    assert fingerprint_a != fingerprint_b

    manifest["models"][1]["revision"] = "not-the-pinned-snapshot"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(QwenRuntimeUnavailable, match="unapproved model revision"):
        backend.generation_fingerprint()


def test_legacy_prompt_without_reference_transcript_is_rebuilt_safely(tmp_path, monkeypatch):
    """Upgrade old four-field prompt files instead of trying a broken ICL call."""
    import json

    FakeQwenModel.calls = []
    fake_module = types.ModuleType("qwen_tts")
    fake_module.Qwen3TTSModel = FakeQwenModel
    monkeypatch.setitem(sys.modules, "qwen_tts", fake_module)
    design = tmp_path / "models" / "design"
    base = tmp_path / "models" / "base"
    design.mkdir(parents=True); base.mkdir(parents=True)
    make_fake_model_folder(design)
    make_fake_model_folder(base)
    profile = VoiceProfile("moses", "Moses", [], "Mature weathered voice", "Moses speaks.")
    assets = tmp_path / "assets"
    original = QwenVoiceBackend(QwenSettings(design, base, "cpu"), assets)
    original.prepare_profiles([profile])

    prompt_path = assets / "moses.prompt.pt"
    payload = torch.load(prompt_path, map_location="cpu", weights_only=True)
    payload.pop("ref_text")  # exact schema used before ICL transcript persistence was fixed
    torch.save(payload, prompt_path)
    meta_path = prompt_path.with_suffix(".prompt.json")
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    metadata.pop("prompt_schema_version", None)
    metadata["prompt_sha256"] = original._file_sha256(prompt_path)
    meta_path.write_text(json.dumps(metadata), encoding="utf-8")

    upgraded = QwenVoiceBackend(QwenSettings(design, base, "cpu"), assets)
    progress = []
    upgraded.prepare_profiles([profile], progress_callback=lambda *args: progress.append(args))
    assert sum(call[0] == "design" for call in FakeQwenModel.calls) == 1
    assert sum(call[0] == "prompt" for call in FakeQwenModel.calls) == 2
    new_metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    assert new_metadata["prompt_schema_version"] == 2
    audio, rate = upgraded.synthesize("Moses speaks with the upgraded voice prompt.", profile)
    assert audio.size and rate == 24000


def test_old_prompt_without_transcript_cannot_be_reused_when_external_wav_is_missing(tmp_path, monkeypatch):
    import json
    import pytest
    from kjv_audio_generator.backend import QwenRuntimeUnavailable

    FakeQwenModel.calls = []
    fake_module = types.ModuleType("qwen_tts")
    fake_module.Qwen3TTSModel = FakeQwenModel
    monkeypatch.setitem(sys.modules, "qwen_tts", fake_module)
    design = tmp_path / "models" / "design"
    base = tmp_path / "models" / "base"
    design.mkdir(parents=True); base.mkdir(parents=True)
    make_fake_model_folder(design)
    make_fake_model_folder(base)
    reference = tmp_path / "external.wav"
    reference.write_bytes(b"external test WAV bytes")
    profile = VoiceProfile("moses", "Moses", [], "Mature voice", "Moses speaks.", str(reference))
    assets = tmp_path / "assets"
    backend = QwenVoiceBackend(QwenSettings(design, base, "cpu"), assets)
    backend.prepare_profiles([profile])
    prompt_path = assets / "moses.prompt.pt"
    payload = torch.load(prompt_path, map_location="cpu", weights_only=True)
    payload.pop("ref_text")
    torch.save(payload, prompt_path)
    meta_path = prompt_path.with_suffix(".prompt.json")
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    metadata.pop("prompt_schema_version", None)
    metadata["prompt_sha256"] = backend._file_sha256(prompt_path)
    meta_path.write_text(json.dumps(metadata), encoding="utf-8")
    reference.unlink()

    restarted = QwenVoiceBackend(QwenSettings(design, base, "cpu"), assets)
    with pytest.raises(QwenRuntimeUnavailable, match="verified saved voice prompt is unavailable"):
        restarted.prepare_profiles([profile])


def _windows_file_allocated_bytes(path):
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_size = kernel32.GetCompressedFileSizeW
    get_size.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
    get_size.restype = wintypes.DWORD
    high = wintypes.DWORD(0)
    ctypes.set_last_error(0)
    low = get_size(str(path), ctypes.byref(high))
    if low == 0xFFFFFFFF and ctypes.get_last_error() != 0:
        raise ctypes.WinError(ctypes.get_last_error())
    return (high.value << 32) | int(low)


def test_fake_qwen_weight_fixtures_are_sparse_on_windows(tmp_path):
    if sys.platform != "win32":
        pytest.skip("NTFS sparse-file allocation check is Windows-only")

    model = make_fake_model_folder(tmp_path / "Qwen3-TTS-12Hz-1.7B-Base")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_attributes = kernel32.GetFileAttributesW
    from ctypes import wintypes
    get_attributes.argtypes = [wintypes.LPCWSTR]
    get_attributes.restype = wintypes.DWORD

    for relative, expected_size in (
        ("model.safetensors", 3_500_000_000),
        ("speech_tokenizer/model.safetensors", 650_000_000),
    ):
        path = model / relative
        assert path.stat().st_size == expected_size
        attributes = get_attributes(str(path))
        assert attributes != 0xFFFFFFFF, ctypes.WinError(ctypes.get_last_error())
        assert attributes & 0x00000200, f"{path} is not marked as a sparse file"
        allocated = _windows_file_allocated_bytes(path)
        assert allocated < 1024 * 1024, (
            f"{path} reserves {allocated:,} bytes on disk for a {expected_size:,}-byte sparse fixture"
        )
