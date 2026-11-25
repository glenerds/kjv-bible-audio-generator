import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


def _load_integrity_tool():
    root = Path(__file__).resolve().parents[1]
    path = root / "tools" / "qwen_asset_integrity.py"
    spec = importlib.util.spec_from_file_location("qwen_asset_integrity_under_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_fake_model(root: Path, folder: str, model_text: bytes, tokenizer_text: bytes):
    model_dir = root / folder
    (model_dir / "speech_tokenizer").mkdir(parents=True)
    (model_dir / "model.safetensors").write_bytes(model_text)
    (model_dir / "speech_tokenizer" / "model.safetensors").write_bytes(tokenizer_text)


def _fake_specs():
    model_bytes = b"test-main-weight-file"
    tokenizer_bytes = b"test-speech-tokenizer-weight-file"
    specs = (
        {
            "repo": "example/VoiceDesign",
            "revision": "a" * 40,
            "folder": "VoiceDesign",
            "kind": "voice_design",
            "files": (
                {
                    "path": "model.safetensors",
                    "manifest_hash": "model_sha256",
                    "manifest_size": "model_bytes",
                    "sha256": hashlib.sha256(model_bytes).hexdigest(),
                },
                {
                    "path": "speech_tokenizer/model.safetensors",
                    "manifest_hash": "speech_tokenizer_sha256",
                    "manifest_size": "speech_tokenizer_bytes",
                    "sha256": hashlib.sha256(tokenizer_bytes).hexdigest(),
                },
            ),
        },
        {
            "repo": "example/Base",
            "revision": "b" * 40,
            "folder": "Base",
            "kind": "base",
            "files": (
                {
                    "path": "model.safetensors",
                    "manifest_hash": "model_sha256",
                    "manifest_size": "model_bytes",
                    "sha256": hashlib.sha256(model_bytes).hexdigest(),
                },
                {
                    "path": "speech_tokenizer/model.safetensors",
                    "manifest_hash": "speech_tokenizer_sha256",
                    "manifest_size": "speech_tokenizer_bytes",
                    "sha256": hashlib.sha256(tokenizer_bytes).hexdigest(),
                },
            ),
        },
    )
    return specs, model_bytes, tokenizer_bytes


def test_pinned_hashes_match_the_published_qwen_file_sha256_values():
    tool = _load_integrity_tool()
    voice, base = tool.PINNED_MODELS
    assert voice["files"][0]["sha256"] == "391e8db219f292c515297cdceeb43e4eae67cdde35fa57e79a6a8a532fca0522"
    assert base["files"][0]["sha256"] == "38fc7fc51c5e776e840414b6fd443962e9411b9654888fd7913e4da643cb857c"
    assert voice["files"][1]["sha256"] == "836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258"
    assert base["files"][1]["sha256"] == voice["files"][1]["sha256"]


def test_sha256_file_streams_and_matches_standard_digest(tmp_path):
    tool = _load_integrity_tool()
    source = tmp_path / "weight.bin"
    payload = bytes(range(256)) * 257
    source.write_bytes(payload)
    assert tool.sha256_file(source, chunk_size=113) == hashlib.sha256(payload).hexdigest()


def test_report_records_verifies_weight_contents_and_emits_manifest_metadata(tmp_path):
    tool = _load_integrity_tool()
    specs, model_bytes, tokenizer_bytes = _fake_specs()
    _write_fake_model(tmp_path, "VoiceDesign", model_bytes, tokenizer_bytes)
    _write_fake_model(tmp_path, "Base", model_bytes, tokenizer_bytes)

    records = tool.report_records(tmp_path, pinned_models=specs)

    assert len(records) == 2
    assert records[0]["model_sha256"] == hashlib.sha256(model_bytes).hexdigest()
    assert records[0]["speech_tokenizer_sha256"] == hashlib.sha256(tokenizer_bytes).hexdigest()
    assert records[0]["model_bytes"] == len(model_bytes)
    assert records[0]["speech_tokenizer_bytes"] == len(tokenizer_bytes)


def test_report_records_fails_closed_for_a_missing_weight_file(tmp_path):
    tool = _load_integrity_tool()
    specs, model_bytes, tokenizer_bytes = _fake_specs()
    _write_fake_model(tmp_path, "VoiceDesign", model_bytes, tokenizer_bytes)
    (tmp_path / "Base" / "speech_tokenizer").mkdir(parents=True)
    (tmp_path / "Base" / "model.safetensors").write_bytes(model_bytes)

    with pytest.raises(tool.AssetIntegrityError, match="missing"):
        tool.report_records(tmp_path, pinned_models=specs)


def test_report_records_rejects_truncated_or_altered_model_weights(tmp_path):
    tool = _load_integrity_tool()
    specs, model_bytes, tokenizer_bytes = _fake_specs()
    _write_fake_model(tmp_path, "VoiceDesign", model_bytes, tokenizer_bytes)
    _write_fake_model(tmp_path, "Base", model_bytes + b"truncated-or-altered", tokenizer_bytes)

    with pytest.raises(tool.AssetIntegrityError, match="SHA-256 mismatch"):
        tool.report_records(tmp_path, pinned_models=specs)


def test_manifest_verification_checks_hashes_sizes_and_pinned_model_identity(tmp_path):
    tool = _load_integrity_tool()
    specs, model_bytes, tokenizer_bytes = _fake_specs()
    _write_fake_model(tmp_path, "VoiceDesign", model_bytes, tokenizer_bytes)
    _write_fake_model(tmp_path, "Base", model_bytes, tokenizer_bytes)
    records = tool.report_records(tmp_path, pinned_models=specs)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({"schema_version": 1, "models": records}),
        encoding="utf-8",
    )

    verified = tool.verify_manifest(tmp_path, manifest_path, pinned_models=specs)
    assert verified == records

    altered = json.loads(manifest_path.read_text(encoding="utf-8"))
    altered["models"][0]["model_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(altered), encoding="utf-8")
    with pytest.raises(tool.AssetIntegrityError, match="manifest mismatch"):
        tool.verify_manifest(tmp_path, manifest_path, pinned_models=specs)


def test_manifest_verification_rejects_duplicate_or_unexpected_model_entries(tmp_path):
    tool = _load_integrity_tool()
    specs, model_bytes, tokenizer_bytes = _fake_specs()
    _write_fake_model(tmp_path, "VoiceDesign", model_bytes, tokenizer_bytes)
    _write_fake_model(tmp_path, "Base", model_bytes, tokenizer_bytes)
    records = tool.report_records(tmp_path, pinned_models=specs)
    manifest_path = tmp_path / "manifest.json"

    manifest_path.write_text(
        json.dumps({"schema_version": 1, "models": records + [records[0]]}),
        encoding="utf-8",
    )
    with pytest.raises(tool.AssetIntegrityError, match="duplicate"):
        tool.verify_manifest(tmp_path, manifest_path, pinned_models=specs)

    manifest_path.write_text(
        json.dumps({"schema_version": 1, "models": [records[0], {**records[1], "repo": "unexpected/model"}]}),
        encoding="utf-8",
    )
    with pytest.raises(tool.AssetIntegrityError, match="exactly"):
        tool.verify_manifest(tmp_path, manifest_path, pinned_models=specs)
