from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import tkinter as tk

import pytest

from kjv_audio_generator.app import GeneratorApp
from kjv_audio_generator.__main__ import main as cli_main


def test_gui_creates_widgets_and_validates_pasted_text():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("No graphical display")
    app = GeneratorApp(root)
    app.text.insert("1.0", "Genesis 1:1 In the beginning.")
    app._validate()
    assert "1 chapters" in app.status.get()
    root.destroy()


def test_cli_self_test_returns_expected_fail_closed_without_models(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys,"argv",["kjv-audio-generator","--self-test","--models",str(tmp_path/"models"),"--output",str(tmp_path/"out")])
    assert cli_main() == 2
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["checks"]["voice_design_model"] is False
    assert payload["checks"]["base_model"] is False
    assert payload["checks"]["model_asset_manifest"] is False
    assert payload["checks"]["qwen_runtime"] is False
    assert payload["checks"]["ffmpeg"] is False


def test_cli_real_audio_smoke_refuses_missing_qwen_models(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [
        "kjv-audio-generator", "--audio-smoke", "--models", str(tmp_path / "models"),
        "--output", str(tmp_path / "out"),
    ])
    assert cli_main() == 3
    assert "Real Qwen audio smoke failed" in capsys.readouterr().err


def test_packaging_recipe_includes_models_audio_encoder_and_portable_launcher():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    script = (root / "tools" / "build_windows.ps1").read_text(encoding="utf-8")
    launcher = (root / "START_KJV_AUDIO_GENERATOR.bat").read_text(encoding="utf-8")
    for token in ("--onedir", "--add-data", "--add-binary", "--collect-all torch", "--collect-all qwen_tts", "--collect-all librosa", "--collect-all torchaudio", "--collect-all accelerate", "speech_tokenizer/model.safetensors"):
        assert token in script
    assert "Qwen3-TTS-12Hz-1.7B-VoiceDesign" in script
    assert "Qwen3-TTS-12Hz-1.7B-Base" in script
    assert "ffmpeg.exe" in script
    assert "kjv_audio_generator/data" in script
    app_source = (root / "src" / "kjv_audio_generator" / "app.py").read_text(encoding="utf-8")
    assert "does not authenticate the translation wording" in app_source
    assert "LICENSES" in script
    assert "portable" in script
    assert "START_KJV_AUDIO_GENERATOR.bat" in script
    assert "developer source tree" in launcher.casefold()


def test_runtime_root_uses_pyinstaller_data_folder(monkeypatch, tmp_path):
    import sys
    from kjv_audio_generator.runtime import runtime_root, bundled_ffmpeg
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "internal"), raising=False)
    assert runtime_root() == (tmp_path / "internal").resolve()
    assert bundled_ffmpeg() == (tmp_path / "internal" / "ffmpeg.exe").resolve()


def test_gui_exposes_safe_stop_and_retry_controls():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("No graphical display")
    app = GeneratorApp(root)
    assert app.stop_button.cget("text") == "Stop safely"
    assert app.stop_button.instate(["disabled"])
    assert app.retry_button.cget("text") == "Retry failed chapters"
    assert app.retry_button.instate(["disabled"])
    root.destroy()


def test_gui_exposes_voice_and_verse_review_controls(tmp_path):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("No graphical display")
    app = GeneratorApp(root)
    app.output_dir.set(str(tmp_path))

    def descendants(widget):
        for child in widget.winfo_children():
            yield child
            yield from descendants(child)

    from tkinter import ttk
    texts = [child.cget("text") for child in descendants(root) if isinstance(child, ttk.Button)]
    assert "Manage Character Voices" in texts
    assert "Review Verse Speakers" in texts

    app._manage_voices()
    root.update_idletasks()
    dialogs = [child for child in root.winfo_children() if isinstance(child, tk.Toplevel)]
    assert dialogs and dialogs[-1].title() == "Manage Character Voice Profiles"
    dialog = dialogs[-1]
    tree_widgets = [child for child in descendants(dialog) if isinstance(child, ttk.Treeview)]
    assert len(tree_widgets) == 1
    assert len(tree_widgets[0].get_children()) >= 5

    entries = [child for child in descendants(dialog) if isinstance(child, ttk.Entry)]
    text_widgets = [child for child in descendants(dialog) if isinstance(child, tk.Text)]
    buttons = {child.cget("text"): child for child in descendants(dialog) if isinstance(child, ttk.Button)}
    assert len(entries) == 4 and len(text_widgets) == 2
    buttons["New Character"].invoke()
    entries[0].delete(0, "end"); entries[0].insert(0, "john_the_baptist")
    entries[1].delete(0, "end"); entries[1].insert(0, "John the Baptist")
    entries[2].delete(0, "end"); entries[2].insert(0, "John, The Baptist")
    text_widgets[0].delete("1.0", "end")
    text_widgets[0].insert("1.0", "Clear, measured adult male voice with a prophetic but restrained tone.")
    text_widgets[1].delete("1.0", "end")
    text_widgets[1].insert("1.0", "Prepare ye the way of the Lord.")
    buttons["Save Voice Profile"].invoke()

    from kjv_audio_generator.voices import VoiceRegistry
    saved = VoiceRegistry.load(tmp_path / "metadata" / "voice_registry.json")
    assert "john_the_baptist" in saved.profiles
    assert saved.get("john_the_baptist").display_name == "John the Baptist"
    assert saved.get("john_the_baptist").status == "not_prepared"
    dialog.destroy()
    root.destroy()


def test_gui_verse_review_saves_exact_multispeaker_segments(tmp_path):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("No graphical display")
    from pathlib import Path
    from tkinter import ttk
    from kjv_audio_generator.attribution import AttributionMap
    from kjv_audio_generator.voices import VoiceRegistry

    app = GeneratorApp(root)
    app.output_dir.set(str(tmp_path))
    source = Path(__file__).resolve().parents[1] / "examples" / "genesis_1_kjv_test.txt"
    app.text.insert("1.0", source.read_text(encoding="utf-8"))
    app._review_verse_speakers()
    root.update_idletasks()
    dialogs = [child for child in root.winfo_children() if isinstance(child, tk.Toplevel)]
    assert dialogs and dialogs[-1].title() == "Review Verse Speaker Assignments"
    dialog = dialogs[-1]

    def descendants(widget):
        for child in widget.winfo_children():
            yield child
            yield from descendants(child)

    combo = next(
        child for child in descendants(dialog)
        if isinstance(child, ttk.Combobox) and "Genesis 1:3" in child.cget("values")
    )
    combo.set("Genesis 1:3")
    buttons = {child.cget("text"): child for child in descendants(dialog) if isinstance(child, ttk.Button)}
    buttons["Load Verse"].invoke()
    text_widgets = [child for child in descendants(dialog) if isinstance(child, tk.Text)]
    assert len(text_widgets) == 2
    text_widgets[1].delete("1.0", "end")
    text_widgets[1].insert("1.0", "narrator\tAnd God said, \ngod\tLet there be light: and there was light.")
    buttons["Save Speaker Segments"].invoke()

    registry = VoiceRegistry.load(tmp_path / "metadata" / "voice_registry.json")
    saved = AttributionMap.load(tmp_path / "metadata" / "speaker_assignments.json", registry)
    assert saved.segment_overrides["Genesis 1:3"] == [
        {"speaker_id": "narrator", "text": "And God said, "},
        {"speaker_id": "god", "text": "Let there be light: and there was light."},
    ]
    dialog.destroy()
    root.destroy()


def test_gui_review_queue_filters_ambiguous_verses_and_clears_them_after_review(tmp_path):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("No graphical display")
    from pathlib import Path
    from tkinter import ttk
    from kjv_audio_generator.attribution import AttributionMap
    from kjv_audio_generator.voices import VoiceRegistry

    registry = VoiceRegistry.defaults()
    metadata = tmp_path / "metadata"
    metadata.mkdir(parents=True)
    registry.save(metadata / "voice_registry.json")
    attribution = AttributionMap(registry, seed_review={
        "Genesis 1:1": ["god", "jesus"],
        "Genesis 1:2": ["moses", "unknown_speaker"],
    })
    attribution.save(metadata / "speaker_assignments.json")

    app = GeneratorApp(root)
    app.output_dir.set(str(tmp_path))
    app.text.insert("1.0", "Genesis 1:1 One verse.\nGenesis 1:2 Another verse.")
    app._review_verse_speakers()
    root.update_idletasks()
    dialogs = [child for child in root.winfo_children() if isinstance(child, tk.Toplevel)]
    dialog = dialogs[-1]

    def descendants(widget):
        for child in widget.winfo_children():
            yield child
            yield from descendants(child)

    combos = [child for child in descendants(dialog) if isinstance(child, ttk.Combobox)]
    assert len(combos) == 2
    filter_combo, ref_combo = combos
    filter_combo.set("Needs review")
    filter_combo.event_generate("<<ComboboxSelected>>")
    root.update_idletasks()
    assert tuple(ref_combo.cget("values")) == ("Genesis 1:1", "Genesis 1:2")
    ref_combo.set("Genesis 1:1")
    ref_combo.event_generate("<<ComboboxSelected>>")
    text_widgets = [child for child in descendants(dialog) if isinstance(child, tk.Text)]
    text_widgets[1].delete("1.0", "end")
    text_widgets[1].insert("1.0", "god\tOne verse.")
    buttons = {child.cget("text"): child for child in descendants(dialog) if isinstance(child, ttk.Button)}
    buttons["Save Speaker Segments"].invoke()
    root.update_idletasks()
    assert tuple(ref_combo.cget("values")) == ("Genesis 1:2",)

    saved = AttributionMap.load(metadata / "speaker_assignments.json", registry)
    assert saved.segment_overrides["Genesis 1:1"] == [{"speaker_id": "god", "text": "One verse."}]
    assert "Genesis 1:1" in saved.seed_review  # audit provenance is retained after manual resolution
    dialog.destroy()
    root.destroy()



def test_cli_no_arguments_still_opens_gui(monkeypatch):
    called = []
    monkeypatch.setattr(sys, "argv", ["KJV Bible Audio Generator.exe"])
    monkeypatch.setattr("kjv_audio_generator.__main__.gui_main", lambda: called.append(True))
    assert cli_main() == 0
    assert called == [True]


def test_cli_gui_flag_opens_gui(monkeypatch):
    called = []
    monkeypatch.setattr(sys, "argv", ["kjv-audio-generator", "--gui"])
    monkeypatch.setattr("kjv_audio_generator.__main__.gui_main", lambda: called.append(True))
    assert cli_main() == 0
    assert called == [True]


def test_cli_self_test_success_checks_models_runtime_and_explicit_ffmpeg(tmp_path, monkeypatch, capsys):
    import subprocess
    import kjv_audio_generator.__main__ as cli

    model_root = tmp_path / "models"
    model_root.mkdir()
    (model_root / "KJV_QWEN_ASSET_MANIFEST.json").write_text("{}", encoding="utf-8")
    ffmpeg = tmp_path / "ffmpeg.exe"

    class FakeBackend:
        def __init__(self, settings, cache):
            self.settings = settings
            self.cache = cache

        def _require_directory(self, folder, label):
            assert folder.is_absolute()

        def generation_fingerprint(self):
            return "verified-model-fingerprint"

        def _imports(self):
            return object()

    monkeypatch.setattr(sys, "argv", [
        "kjv-audio-generator", "--self-test", "--models", str(model_root),
        "--ffmpeg", str(ffmpeg), "--output", str(tmp_path / "out"),
    ])
    monkeypatch.setattr(cli, "QwenVoiceBackend", FakeBackend)
    monkeypatch.setattr("kjv_audio_generator.audio.find_ffmpeg", lambda path=None: str(ffmpeg))
    monkeypatch.setattr(cli.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a[0], 0, "ffmpeg version test\n", ""))

    assert cli_main() == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert all(payload["checks"].values())
    assert payload["ffmpeg"]["version"] == "ffmpeg version test"


def test_cli_audio_smoke_success_uses_real_workflow_contract(tmp_path, monkeypatch, capsys):
    import kjv_audio_generator.__main__ as cli

    class FakeBackend:
        def __init__(self, settings, cache):
            self.prepared = []

        def prepare_profiles(self, profiles):
            self.prepared.extend(profiles)

        def synthesize(self, text, profile):
            assert text.startswith("This is a test")
            assert profile.speaker_id == "narrator"
            return [0.0] * 128, 24000

    class FakeAssembler:
        def __init__(self, output, ffmpeg, bitrate):
            self.output = output

        def write_chapter(self, book, chapter, segments, audio):
            assert (book, chapter) == ("Genesis", 1)
            assert len(segments) == len(audio) == 1
            return self.output / "Genesis_001.mp3", self.output / "Genesis_001.cues.json"

    monkeypatch.setattr(sys, "argv", [
        "kjv-audio-generator", "--audio-smoke", "--models", str(tmp_path / "models"),
        "--output", str(tmp_path / "out"),
    ])
    monkeypatch.setattr(cli, "QwenVoiceBackend", FakeBackend)
    monkeypatch.setattr(cli, "ChapterAudioAssembler", FakeAssembler)

    assert cli_main() == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["samples"] == 128
    assert payload["sample_rate"] == 24000


def test_cli_speaker_projection_import_persists_registry_assignments_and_review(tmp_path, monkeypatch, capsys):
    import json
    from kjv_audio_generator.attribution import AttributionMap
    from kjv_audio_generator.voices import VoiceRegistry

    projections = tmp_path / "projections.tsv"
    projections.write_text(
        "START VS\tEND VS\tSPEAKER (FCBH)\tALT SPEAKER (FCBH)\n"
        "GEN 1:1\tGEN 1:1\tMoses\t\n",
        encoding="utf-8",
    )
    output = tmp_path / "output"
    monkeypatch.setattr(sys, "argv", [
        "kjv-audio-generator", "--speaker-projections", str(projections),
        "--output", str(output),
    ])

    assert cli_main() == 0
    report = json.loads(capsys.readouterr().out)
    metadata = output / "metadata"
    registry = VoiceRegistry.load(metadata / "voice_registry.json")
    assignments = AttributionMap.load(metadata / "speaker_assignments.json", registry)
    review = json.loads((metadata / "speaker_seed_review.json").read_text(encoding="utf-8"))
    assert report["source_rows"] == 1
    assert report["uniquely_mapped_verses"] == 1
    assert registry.get("moses").display_name == "Moses"
    assert assignments.ranges[0].speaker_id == "moses"
    assert review["summary"]["requires_review"] is True


def test_cli_speaker_projection_import_preserves_manual_work_and_registry(tmp_path, monkeypatch, capsys):
    import json
    from kjv_audio_generator.attribution import AttributionMap, SpeakerRange
    from kjv_audio_generator.models import Verse, VerseRef
    from kjv_audio_generator.voices import VoiceProfile, VoiceRegistry

    output = tmp_path / "output"
    metadata = output / "metadata"
    metadata.mkdir(parents=True)
    registry = VoiceRegistry.defaults()
    registry.add(VoiceProfile(
        "custom_elizabeth", "Elizabeth Custom", ["Elizabeth"],
        "A user-authored, prepared voice profile.", status="prepared",
    ))
    registry.save(metadata / "voice_registry.json")
    existing = AttributionMap(
        registry,
        ranges=[SpeakerRange("Genesis", 1, 3, 3, "god")],
        segment_overrides={"Genesis 1:1": [{"speaker_id": "narrator", "text": "Manual exact verse."}]},
        seed_review={"Genesis 1:8": ["god"]},
        provenance={"dataset": "user-reviewed-custom", "origin_note": "preserve this"},
    )
    existing.save(metadata / "speaker_assignments.json")

    projections = tmp_path / "projections.tsv"
    projections.write_text(
        "START VS\tEND VS\tSPEAKER (FCBH)\tALT SPEAKER (FCBH)\n"
        "GEN 1:1\tGEN 1:1\tMoses\t\n"
        "GEN 1:2\tGEN 1:2\tMoses\tGod\n"
        "GEN 1:3\tGEN 1:3\tJesus\t\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", [
        "kjv-audio-generator", "--speaker-projections", str(projections),
        "--output", str(output),
    ])

    assert cli_main() == 0
    first_report = json.loads(capsys.readouterr().out)
    saved_registry = VoiceRegistry.load(metadata / "voice_registry.json")
    saved = AttributionMap.load(metadata / "speaker_assignments.json", saved_registry)
    review = json.loads((metadata / "speaker_seed_review.json").read_text(encoding="utf-8"))

    assert saved_registry.get("custom_elizabeth").status == "prepared"
    assert saved_registry.get("moses").display_name == "Moses"
    assert saved.segment_overrides["Genesis 1:1"] == [
        {"speaker_id": "narrator", "text": "Manual exact verse."}
    ]
    assert saved.segments_for(Verse(VerseRef("Genesis", 1, 1), "Manual exact verse."))[0].speaker_id == "narrator"
    assert any(r.speaker_id == "god" and r.start_verse == 3 for r in saved.ranges)
    assert saved.seed_review["Genesis 1:8"] == ["god"]
    assert set(saved.seed_review["Genesis 1:2"]) == {"god", "moses"}
    assert set(saved.seed_review["Genesis 1:3"]) == {"god", "jesus"}
    assert saved.segments_for(Verse(VerseRef("Genesis", 1, 3), "Conflicting source suggestions."))[0].speaker_id == "unknown_speaker"
    assert review["ambiguous_verse_candidates"]["Genesis 1:8"] == ["god"]
    assert review["merge"]["preserved_manual_overrides"] == 1
    assert first_report["merge"]["preserved_existing_ranges"] == 1
    assert saved.provenance["origin_note"] == "preserve this"
    assert len(saved.provenance["import_history"]) == 1

    # Re-importing the same source replaces its prior suggestions, not the
    # previously preserved user range, profile or verse override.
    assert cli_main() == 0
    second_report = json.loads(capsys.readouterr().out)
    registry_again = VoiceRegistry.load(metadata / "voice_registry.json")
    saved_again = AttributionMap.load(metadata / "speaker_assignments.json", registry_again)
    assert saved_again.segment_overrides == saved.segment_overrides
    assert registry_again.get("custom_elizabeth").status == "prepared"
    assert any(r.speaker_id == "god" and r.start_verse == 3 for r in saved_again.ranges)
    assert len(saved_again.provenance["import_history"]) == 1
    assert second_report["merge"]["merged_ranges"] == first_report["merge"]["merged_ranges"]
    assert second_report["merge"]["preserved_existing_ranges"] == 1


def test_json_metadata_write_is_atomic_when_replace_fails(tmp_path, monkeypatch):
    import kjv_audio_generator.json_io as json_io
    from kjv_audio_generator.__main__ import _write_json_atomic

    target = tmp_path / "speaker_seed_review.json"
    original = b'{"previous": true}\n'
    target.write_bytes(original)

    def fail_replace(source, destination):
        raise OSError("simulated atomic replace failure")

    monkeypatch.setattr(json_io.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated atomic replace failure"):
        _write_json_atomic(target, {"new": True})

    assert target.read_bytes() == original
    assert not list(tmp_path.glob(".*.tmp"))


def test_cli_speaker_projection_import_reports_missing_file(tmp_path, monkeypatch, capsys):
    missing = tmp_path / "not-present.tsv"
    monkeypatch.setattr(sys, "argv", [
        "kjv-audio-generator", "--speaker-projections", str(missing),
        "--output", str(tmp_path / "output"),
    ])
    assert cli_main() == 1
    assert "Speaker data import failed" in capsys.readouterr().err


def test_cli_input_wires_parse_backend_queue_and_report_without_model_inference(tmp_path, monkeypatch, capsys):
    import kjv_audio_generator.__main__ as cli
    from kjv_audio_generator.attribution import AttributionMap

    fixture = tmp_path / "complete_bible.json"
    fixture.write_text("{}", encoding="utf-8")
    output = tmp_path / "output"
    calls = {}

    class FakeDocument:
        chapters = [object()]

        def validate_complete(self):
            calls["validated"] = True
            return {"complete": True, "books": 66, "chapters": 1189, "verses": 31102}

    class FakeBackend:
        def __init__(self, settings, cache):
            calls["backend"] = True

    class FakeAssembler:
        def __init__(self, out, ffmpeg, bitrate):
            calls["assembler"] = (out, bitrate)

    class FakeWorker:
        def __init__(self, document, out, registry, attribution, backend, assembler):
            calls["chapters"] = len(document.chapters)
            self.store = self

        def start(self, background=False):
            calls["background"] = background

        def progress(self):
            return {"complete": 1, "pending": 0, "failed": 0}

    monkeypatch.setattr(sys, "argv", [
        "kjv-audio-generator", "--input", str(fixture), "--output", str(output),
    ])
    monkeypatch.setattr(cli, "parse_path", lambda path: FakeDocument())
    monkeypatch.setattr(cli, "QwenVoiceBackend", FakeBackend)
    monkeypatch.setattr(cli, "ChapterAudioAssembler", FakeAssembler)
    monkeypatch.setattr(cli, "ChapterWorker", FakeWorker)
    monkeypatch.setattr(cli, "load_or_seed_attribution", lambda out, data, registry: AttributionMap(registry))

    assert cli_main() == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert calls["validated"] is True
    assert calls["backend"] is True
    assert calls["chapters"] == 1
    assert calls["background"] is False
    assert payload["counts"]["complete"] == 1
    assert output.is_dir()


def test_gui_speaker_import_preserves_reviewed_work_and_merges_conflicts(tmp_path, monkeypatch):
    import json
    from kjv_audio_generator.app import GeneratorApp
    from kjv_audio_generator.attribution import AttributionMap, SpeakerRange
    from kjv_audio_generator.voices import VoiceProfile, VoiceRegistry
    from kjv_audio_generator.models import Verse, VerseRef

    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("No graphical display")

    output = tmp_path / "output"
    metadata = output / "metadata"
    metadata.mkdir(parents=True)
    registry = VoiceRegistry.defaults()
    registry.add(VoiceProfile(
        "custom_elizabeth", "Custom Elizabeth", [],
        "Clear, measured adult female voice for this project.", status="prepared",
    ))
    registry.save(metadata / "voice_registry.json")
    existing = AttributionMap(
        registry,
        ranges=[SpeakerRange("Genesis", 1, 3, 3, "god", priority=7)],
        segment_overrides={
            "Genesis 1:1": [
                {"speaker_id": "narrator", "text": "Manual exact verse."}
            ]
        },
        seed_review={"Genesis 1:8": ["god"]},
        provenance={"dataset": "user-reviewed-custom", "origin_note": "keep my edits"},
    )
    existing.save(metadata / "speaker_assignments.json")

    projections = tmp_path / "projections.tsv"
    projections.write_text(
        "START VS\tEND VS\tSPEAKER (FCBH)\tALT SPEAKER (FCBH)\n"
        "GEN 1:1\tGEN 1:1\tMoses\t\n"
        "GEN 1:3\tGEN 1:3\tJesus\t\n",
        encoding="utf-8",
    )
    selected = iter([str(projections), ""])
    monkeypatch.setattr(
        "kjv_audio_generator.app.filedialog.askopenfilename",
        lambda **_kwargs: next(selected),
    )
    monkeypatch.setattr("kjv_audio_generator.app.messagebox.showinfo", lambda *a, **k: None)
    monkeypatch.setattr("kjv_audio_generator.app.messagebox.showerror", lambda *a, **k: pytest.fail(str(a)))

    app = GeneratorApp(root)
    app.output_dir.set(str(output))
    app._import_speaker_data()

    saved_registry = VoiceRegistry.load(metadata / "voice_registry.json")
    saved = AttributionMap.load(metadata / "speaker_assignments.json", saved_registry)
    review = json.loads((metadata / "speaker_seed_review.json").read_text(encoding="utf-8"))

    assert saved_registry.get("custom_elizabeth").status == "prepared"
    assert saved.segment_overrides["Genesis 1:1"] == [
        {"speaker_id": "narrator", "text": "Manual exact verse."}
    ]
    assert saved.segments_for(Verse(VerseRef("Genesis", 1, 1), "Manual exact verse."))[0].speaker_id == "narrator"
    assert saved.provenance["origin_note"] == "keep my edits"
    assert saved.seed_review["Genesis 1:8"] == ["god"]
    assert any(r.speaker_id == "god" and r.start_verse == 3 for r in saved.ranges)
    assert any(r.speaker_id == "jesus" and r.start_verse == 3 for r in saved.ranges)
    assert set(saved.seed_review["Genesis 1:3"]) == {"god", "jesus"}
    assert saved.segments_for(Verse(VerseRef("Genesis", 1, 3), "An uncertain quotation."))[0].speaker_id == "unknown_speaker"
    assert review["merge"]["preserved_manual_overrides"] == 1
    assert review["ambiguous_verse_candidates"]["Genesis 1:3"] == ["god", "jesus"]
    assert app.registry is not None and app.attribution is not None

    # The same GUI import is safe to repeat: the previous source's projections
    # are replaced, not duplicated, while human edits remain intact.
    selected = iter([str(projections), ""])
    monkeypatch.setattr(
        "kjv_audio_generator.app.filedialog.askopenfilename",
        lambda **_kwargs: next(selected),
    )
    app._import_speaker_data()
    again_registry = VoiceRegistry.load(metadata / "voice_registry.json")
    again = AttributionMap.load(metadata / "speaker_assignments.json", again_registry)
    assert again.segment_overrides == saved.segment_overrides
    assert again.provenance["origin_note"] == "keep my edits"
    assert len(again.provenance["import_history"]) == 1
    assert again.provenance["suggestion_sources"] == saved.provenance["suggestion_sources"]
    root.destroy()



def test_packaged_launcher_dispatches_through_the_cli_main_entrypoint():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    entrypoint = (root / "tools" / "entrypoint.py").read_text(encoding="utf-8")
    assert "from kjv_audio_generator.__main__ import main" in entrypoint
    assert "raise SystemExit(_exit_code)" in entrypoint


def test_windowed_cli_self_test_writes_report_when_stdout_and_stderr_are_missing(tmp_path, monkeypatch):
    from pathlib import Path
    import json
    import subprocess
    import kjv_audio_generator.__main__ as cli
    import kjv_audio_generator.audio as audio

    model_root = tmp_path / "models"
    model_root.mkdir()
    (model_root / "KJV_QWEN_ASSET_MANIFEST.json").write_text("{}", encoding="utf-8")
    output = tmp_path / "portable-output"
    ffmpeg = tmp_path / "ffmpeg.exe"
    ffmpeg.write_bytes(b"test-ffmpeg")

    class FakeBackend:
        def __init__(self, settings, cache):
            self.settings = settings
            Path(cache).mkdir(parents=True, exist_ok=True)

        def _require_directory(self, folder, label):
            return None

        def generation_fingerprint(self):
            return "verified-model-fingerprint"

        def _imports(self):
            return object()

    monkeypatch.setattr(sys, "argv", [
        "KJV Bible Audio Generator.exe",
        "--self-test",
        "--models", str(model_root),
        "--output", str(output),
    ])
    monkeypatch.setattr(cli, "QwenVoiceBackend", FakeBackend)
    monkeypatch.setattr(cli, "bundled_ffmpeg", lambda: ffmpeg)
    monkeypatch.setattr(audio, "find_ffmpeg", lambda path=None: str(ffmpeg))
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "ffmpeg version test\n", ""),
    )
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    assert cli.main() == 0
    report_path = output / "metadata" / "self_test_report.json"
    assert report_path.is_file()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert all(payload["checks"].values())
    assert payload["ffmpeg"]["version"] == "ffmpeg version test"


def test_native_windows_package_acceptance_builds_runs_and_relocates_the_frozen_app():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "windows-package-acceptance.yml").read_text(encoding="utf-8")
    script = (root / "tools" / "windows_package_acceptance.ps1").read_text(encoding="utf-8")
    for token in (
        "runs-on: windows-latest",
        "timeout-minutes: 180",
        "windows_package_acceptance.ps1",
        "-TorchVariant cu128",
        "WINDOWS_PORTABLE_PACKAGE_ACCEPTANCE_PASSED",
        "subst drive-letter",
    ):
        assert token in workflow + script
    for token in (
        "$BuildScript = Join-Path $PSScriptRoot 'build_windows.ps1'",
        "--self-test",
        "--audio-smoke",
        "self_test_report.json",
        "audio_smoke_report.json",
        "KJV Bible Audio Generator.exe",
        "ffmpeg.exe",
        "Move-Item -LiteralPath $DistRoot -Destination $RelocatedRoot",
        "$SubstCommand = 'subst {0} \"{1}\"'",
        "& $env:ComSpec /c $SubstCommand",
        "relocated-self-test-report.json",
        "relocated-audio-smoke-report.json",
        "KJV_APP_DIAGNOSTICS_FILE",
        "self-test-entrypoint-diagnostics.json",
        "function Invoke-PackagedExecutable",
        "[System.Diagnostics.ProcessStartInfo]::new()",
        "$StartInfo.ArgumentList.Add",
        "$Process.WaitForExit($TimeoutSeconds * 1000)",
        "$Process.Kill()",
        "-TimeoutSeconds 1800",
    ):
        assert token in script


def test_windows_package_acceptance_downloads_assets_before_forcing_offline_mode():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    script = (root / "tools" / "windows_package_acceptance.ps1").read_text(encoding="utf-8")
    build_at = script.index("& $BuildScript -TorchVariant $TorchVariant")
    offline_at = script.index("[Environment]::SetEnvironmentVariable($Name, '1', 'Process')")
    self_test_at = script.index("$Executable --self-test")
    assert build_at < offline_at < self_test_at
    assert "subst {0}" in script
    assert "subst $DriveLetter /D" in script



def test_frozen_entrypoint_writes_opt_in_diagnostics_even_when_console_streams_are_missing():
    root = Path(__file__).resolve().parents[1]
    entrypoint = (root / "tools" / "entrypoint.py").read_text(encoding="utf-8")
    for token in (
        "KJV_APP_DIAGNOSTICS_FILE",
        "sys.argv",
        "sys.executable",
        "sys.stdout is None",
        "sys.stderr is None",
        '_record_entrypoint_diagnostics("started")',
        '_record_entrypoint_diagnostics("exception"',
        '_record_entrypoint_diagnostics("completed"',
        "os.replace(temporary, destination)",
    ):
        assert token in entrypoint
