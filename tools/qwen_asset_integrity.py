from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


class AssetIntegrityError(ValueError):
    """Raised when a pinned Qwen checkpoint is missing or does not match."""


# These are the SHA-256 values published by Hugging Face for the exact pinned
# repository revisions below. They are file-content SHA-256 values, not Xet
# chunk hashes. The speech-tokenizer weight file is identical in both snapshots.
PINNED_MODELS: tuple[dict[str, Any], ...] = (
    {
        "repo": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        "revision": "5ecdb67327fd37bb2e042aab12ff7391903235d3",
        "folder": "Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        "kind": "voice_design",
        "files": (
            {
                "path": "model.safetensors",
                "manifest_hash": "model_sha256",
                "manifest_size": "model_bytes",
                "sha256": "391e8db219f292c515297cdceeb43e4eae67cdde35fa57e79a6a8a532fca0522",
            },
            {
                "path": "speech_tokenizer/model.safetensors",
                "manifest_hash": "speech_tokenizer_sha256",
                "manifest_size": "speech_tokenizer_bytes",
                "sha256": "836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258",
            },
        ),
    },
    {
        "repo": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "revision": "fd4b254389122332181a7c3db7f27e918eec64e3",
        "folder": "Qwen3-TTS-12Hz-1.7B-Base",
        "kind": "base",
        "files": (
            {
                "path": "model.safetensors",
                "manifest_hash": "model_sha256",
                "manifest_size": "model_bytes",
                "sha256": "38fc7fc51c5e776e840414b6fd443962e9411b9654888fd7913e4da643cb857c",
            },
            {
                "path": "speech_tokenizer/model.safetensors",
                "manifest_hash": "speech_tokenizer_sha256",
                "manifest_size": "speech_tokenizer_bytes",
                "sha256": "836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258",
            },
        ),
    },
)


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    """Hash a potentially multi-gigabyte file without loading it into memory."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while True:
            chunk = source.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def report_records(
    models_root: Path,
    pinned_models: tuple[dict[str, Any], ...] | None = None,
) -> list[dict[str, Any]]:
    """Verify every pinned weight file and return manifest-ready metadata."""
    models_root = Path(models_root)
    specs = PINNED_MODELS if pinned_models is None else pinned_models
    records: list[dict[str, Any]] = []

    for spec in specs:
        folder = models_root / str(spec["folder"])
        record: dict[str, Any] = {
            "repo": spec["repo"],
            "revision": spec["revision"],
            "folder": spec["folder"],
            "kind": spec["kind"],
        }
        for file_spec in spec["files"]:
            relative_path = str(file_spec["path"])
            file_path = folder / relative_path
            if not file_path.is_file():
                raise AssetIntegrityError(
                    f"Required pinned weight file is missing: {spec['repo']}/{relative_path}"
                )
            actual_hash = sha256_file(file_path)
            expected_hash = str(file_spec["sha256"]).lower()
            if actual_hash != expected_hash:
                raise AssetIntegrityError(
                    f"SHA-256 mismatch for {spec['repo']}/{relative_path}: "
                    f"expected {expected_hash}, got {actual_hash}. "
                    "The checkpoint is incomplete, altered, or from a different revision."
                )
            record[str(file_spec["manifest_hash"])] = actual_hash
            record[str(file_spec["manifest_size"])] = file_path.stat().st_size
        records.append(record)

    return records


def verify_manifest(
    models_root: Path,
    manifest_path: Path,
    pinned_models: tuple[dict[str, Any], ...] | None = None,
) -> list[dict[str, Any]]:
    """Re-hash the pinned weights and compare them with the build manifest."""
    records = report_records(models_root, pinned_models=pinned_models)
    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AssetIntegrityError(f"Could not read Qwen asset manifest: {exc}") from exc

    if not isinstance(manifest, dict) or type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
        raise AssetIntegrityError("Qwen asset manifest must be a schema_version 1 JSON object.")

    manifest_models = manifest.get("models")
    if not isinstance(manifest_models, list):
        raise AssetIntegrityError("Qwen asset manifest models must be a JSON array.")

    by_repo: dict[str, dict[str, Any]] = {}
    for entry in manifest_models:
        if not isinstance(entry, dict) or not isinstance(entry.get("repo"), str):
            raise AssetIntegrityError("Qwen asset manifest contains an invalid model entry.")
        repo = entry["repo"]
        if repo in by_repo:
            raise AssetIntegrityError(f"Qwen asset manifest contains a duplicate model entry: {repo}")
        by_repo[repo] = entry

    if set(by_repo) != {str(record["repo"]) for record in records}:
        raise AssetIntegrityError("Qwen asset manifest does not contain exactly the two pinned Qwen models.")

    required_fields = (
        "repo",
        "revision",
        "folder",
        "kind",
        "model_sha256",
        "speech_tokenizer_sha256",
        "model_bytes",
        "speech_tokenizer_bytes",
    )
    for record in records:
        entry = by_repo[str(record["repo"])]
        for field in required_fields:
            if entry.get(field) != record.get(field):
                raise AssetIntegrityError(
                    f"Qwen asset manifest mismatch for {record['repo']} field {field}: "
                    f"expected {record.get(field)!r}, got {entry.get(field)!r}"
                )
    return records


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify Qwen3-TTS weights against pinned Hugging Face SHA-256 values."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    report_parser = subparsers.add_parser(
        "report", help="verify pinned weights and print manifest-ready JSON records"
    )
    report_parser.add_argument("--models-root", type=Path, required=True)

    verify_parser = subparsers.add_parser(
        "verify", help="verify pinned weights and their manifest entries"
    )
    verify_parser.add_argument("--models-root", type=Path, required=True)
    verify_parser.add_argument("--manifest", type=Path, required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "report":
            records = report_records(args.models_root)
            print(json.dumps(records, ensure_ascii=False, separators=(",", ":")))
        else:
            records = verify_manifest(args.models_root, args.manifest)
            print(f"Verified pinned SHA-256 hashes for {len(records)} Qwen model snapshots.")
    except (AssetIntegrityError, OSError, ValueError) as exc:
        print(f"Qwen asset integrity error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
