from __future__ import annotations

import argparse
import json
import sys
import shutil
import subprocess
from pathlib import Path

from .app import main as gui_main
from .attribution import AttributionMap
from .audio import ChapterAudioAssembler
from .backend import QwenRuntimeUnavailable, QwenSettings, QwenVoiceBackend
from .parser import parse_path
from .storage import QueueStore
from .voices import VoiceRegistry
from .worker import ChapterWorker
from .runtime import bundled_ffmpeg, runtime_root
from .attribution_seed import import_clear_speaker_seed, load_or_seed_attribution, merge_seed_suggestions
from .json_io import write_json_atomic


def _write_json_atomic(path: Path, payload: object) -> None:
    """Compatibility wrapper for the shared crash-safe JSON writer."""
    write_json_atomic(path, payload)


def _emit_cli_json(path: Path, payload: dict[str, object]) -> None:
    """Persist CLI reports even when PyInstaller's windowed executable has no console."""
    _write_json_atomic(path, payload)
    stream = sys.stdout
    if stream is not None:
        try:
            print(json.dumps(payload, indent=2, ensure_ascii=False), file=stream)
        except (OSError, ValueError):
            # A windowed executable may have stdout attached to an already-closed stream.
            pass


def _emit_cli_error(message: str) -> None:
    stream = sys.stderr
    if stream is not None:
        try:
            print(message, file=stream)
        except (OSError, ValueError):
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate individual KJV chapter MP3s with persistent character voices")
    parser.add_argument("--gui", action="store_true", help="Open the desktop application")
    parser.add_argument("--input", type=Path, help="Bible text file (.usfm, .sfm, .txt, .json, .zip)")
    parser.add_argument("--output", type=Path, default=Path("KJV_Bible_Audio"))
    parser.add_argument("--models", type=Path, help="Model folder (defaults to the bundled models directory)")
    parser.add_argument("--speaker-projections", type=Path, help="Import provisional Clear/MACULA speaker ranges from a TSV")
    parser.add_argument("--speaker-details", type=Path, help="Optional character details TSV for speaker voice descriptions")
    parser.add_argument("--ffmpeg", type=Path)
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda:0"])
    parser.add_argument("--bitrate", type=int, default=96, choices=[64,80,96,112,128,160,192])
    parser.add_argument("--self-test", action="store_true", help="Check the real Qwen runtime and model folders; no audio is synthesized")
    parser.add_argument("--audio-smoke", action="store_true", help="Generate a short actual-Qwen audio file using the narrator profile")
    args = parser.parse_args()

    if args.gui or (not args.input and not args.self_test and not args.audio_smoke and not args.speaker_projections):
        gui_main(); return 0
    model_root = args.models.resolve() if args.models else runtime_root() / "models"
    design = model_root / "Qwen3-TTS-12Hz-1.7B-VoiceDesign"
    base = model_root / "Qwen3-TTS-12Hz-1.7B-Base"
    settings = QwenSettings(design, base, args.device)
    ffmpeg_path = args.ffmpeg or (bundled_ffmpeg() if bundled_ffmpeg().is_file() else None)
    if args.self_test:
        checks = {"voice_design_model": False, "base_model": False, "model_asset_manifest": False, "qwen_runtime": False, "ffmpeg": False}
        errors = []
        backend = QwenVoiceBackend(settings, args.output / "metadata" / "voice_assets")
        for key, folder, label in (
            ("voice_design_model", design, "VoiceDesign"),
            ("base_model", base, "Base"),
        ):
            try:
                backend._require_directory(folder, label)
                checks[key] = True
            except Exception as exc:
                errors.append(str(exc))
        try:
            manifest_path = model_root / "KJV_QWEN_ASSET_MANIFEST.json"
            if not manifest_path.is_file():
                raise RuntimeError(f"Pinned Qwen asset manifest is missing: {manifest_path}")
            backend.generation_fingerprint()
            checks["model_asset_manifest"] = True
        except Exception as exc:
            errors.append(str(exc))
        try:
            backend._imports()
            checks["qwen_runtime"] = True
        except Exception as exc:
            errors.append(str(exc))
        try:
            from .audio import find_ffmpeg
            if not bundled_ffmpeg().is_file() and not args.ffmpeg:
                raise RuntimeError(f"Bundled ffmpeg.exe is missing: {bundled_ffmpeg()}")
            executable = find_ffmpeg(ffmpeg_path)
            result = subprocess.run([executable, "-version"], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise RuntimeError(result.stderr[-1000:] or "FFmpeg version check failed")
            checks["ffmpeg"] = True
            ffmpeg_info = {"path": executable, "bundled": bool(bundled_ffmpeg().is_file()), "version": result.stdout.splitlines()[0] if result.stdout else "unknown"}
        except Exception as exc:
            errors.append(str(exc))
            ffmpeg_info = {"path": str(ffmpeg_path) if ffmpeg_path else shutil.which("ffmpeg"), "bundled": bool(bundled_ffmpeg().is_file())}
        ok = all(checks.values())
        payload = {
            "ok": ok,
            "checks": checks,
            "errors": errors,
            "voice_design_model": str(design),
            "base_model": str(base),
            "ffmpeg": ffmpeg_info,
            "note": "Preflight only; it does not synthesize real speech.",
        }
        _emit_cli_json(args.output / "metadata" / "self_test_report.json", payload)
        return 0 if ok else 2
    if args.audio_smoke:
        try:
            registry = VoiceRegistry.defaults(); backend = QwenVoiceBackend(settings, args.output / "metadata" / "voice_assets")
            profile = registry.get("narrator"); backend.prepare_profiles([profile])
            samples, sr = backend.synthesize("This is a test of the King James Bible narrator voice.", profile)
            assembler = ChapterAudioAssembler(args.output, ffmpeg_path, args.bitrate)
            from .models import SpeechSegment, VerseRef
            seg = SpeechSegment(VerseRef("Genesis",1,1),0,"narrator","This is a test of the King James Bible narrator voice.")
            mp3, cue = assembler.write_chapter("Genesis",0+1,[seg],[(samples,sr)])
            payload = {
                "ok": True,
                "audio": str(mp3),
                "cue": str(cue),
                "samples": len(samples),
                "sample_rate": sr,
            }
            _emit_cli_json(args.output / "metadata" / "audio_smoke_report.json", payload)
            return 0
        except Exception as exc:
            payload = {
                "ok": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            try:
                _emit_cli_json(args.output / "metadata" / "audio_smoke_report.json", payload)
            except OSError:
                pass
            _emit_cli_error(f"Real Qwen audio smoke failed: {type(exc).__name__}: {exc}")
            return 3
    if args.speaker_projections:
        try:
            out = args.output.resolve()
            metadata = out / "metadata"
            registry_path = metadata / "voice_registry.json"
            registry = VoiceRegistry.load(registry_path) if registry_path.is_file() else VoiceRegistry.defaults()
            assignments_path = metadata / "speaker_assignments.json"
            existing = AttributionMap.load(assignments_path, registry) if assignments_path.is_file() else None
            attribution, report, review = import_clear_speaker_seed(args.speaker_projections, args.speaker_details, registry)
            attribution, merge_report = merge_seed_suggestions(existing, attribution)
            metadata.mkdir(parents=True, exist_ok=True)
            registry.save(registry_path)
            attribution.save(assignments_path)
            review["ambiguous_verse_candidates"] = attribution.seed_review
            review["merge"] = merge_report
            _write_json_atomic(metadata / "speaker_seed_review.json", review)
            payload = report.to_dict()
            payload["merge"] = merge_report
            print(json.dumps(payload, indent=2))
            return 0
        except Exception as exc:
            print(f"Speaker data import failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
    if not args.input:
        parser.error("--input is required unless --gui, --self-test, --audio-smoke or --speaker-projections is selected")
    try:
        doc = parse_path(args.input)
        validation = doc.validate_complete()
        out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
        registry = VoiceRegistry.load(out / "metadata" / "voice_registry.json") if (out / "metadata" / "voice_registry.json").is_file() else VoiceRegistry.defaults()
        attribution = load_or_seed_attribution(out, runtime_root(), registry)
        backend = QwenVoiceBackend(settings, out / "metadata" / "voice_assets")
        assembler = ChapterAudioAssembler(out, ffmpeg_path, args.bitrate)
        worker = ChapterWorker(doc, out, registry, attribution, backend, assembler)
        worker.start(background=False)
        counts = worker.store.progress()
        print(json.dumps({"import_validation": validation, "counts":counts,"report":str(out / "metadata" / "generation_report.json")}, indent=2))
        return 1 if counts["failed"] or counts["pending"] else 0
    except Exception as exc:
        print(f"Generation failed: {type(exc).__name__}: {exc}", file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
