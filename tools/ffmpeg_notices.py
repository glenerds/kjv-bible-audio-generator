"""Import and verify the complete FFmpeg package documentation/notices set."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_symlinks(root: Path, description: str) -> None:
    """Reject a symlink root or any symlink below it without following links."""
    if root.is_symlink():
        raise ValueError(f"Symlinks are not permitted in {description}: {root}")
    if root.is_dir():
        for path in root.rglob("*"):
            if path.is_symlink():
                raise ValueError(f"Symlinks are not permitted in {description}: {path}")




def _reject_alternate_data_streams(root: Path, description: str) -> None:
    """Reject NTFS alternate data streams, which normal Path listings hide."""
    if os.name != "nt":
        return

    import ctypes
    from ctypes import wintypes

    class Win32FindStreamData(ctypes.Structure):
        _fields_ = [
            ("StreamSize", ctypes.c_longlong),
            ("cStreamName", wintypes.WCHAR * (260 + 36)),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    find_first = kernel32.FindFirstStreamW
    find_first.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.POINTER(Win32FindStreamData),
        wintypes.DWORD,
    ]
    find_first.restype = wintypes.HANDLE
    find_next = kernel32.FindNextStreamW
    find_next.argtypes = [wintypes.HANDLE, ctypes.POINTER(Win32FindStreamData)]
    find_next.restype = wintypes.BOOL
    find_close = kernel32.FindClose
    find_close.argtypes = [wintypes.HANDLE]
    find_close.restype = wintypes.BOOL

    if root.is_file():
        candidates = (root,)
    elif root.is_dir():
        # Directories can also carry named $DATA streams even though they do
        # not have the default unnamed data stream. Inspect the root and every
        # descendant, not just regular files.
        candidates = (root, *root.rglob("*"))
    else:
        raise ValueError(f"Cannot inspect alternate data streams in {description}: {root}")

    invalid_handle = ctypes.c_void_p(-1).value
    # Filesystems without stream support report ERROR_INVALID_PARAMETER;
    # some report INVALID_FUNCTION / NOT_SUPPORTED instead. Empty directories
    # report ERROR_HANDLE_EOF because they have no $DATA streams. Other errors
    # are fail-closed rather than silently skipping stream inspection.
    unsupported_errors = {1, 50, 87}
    error_handle_eof = 38
    for path in candidates:
        stream_data = Win32FindStreamData()
        handle = find_first(str(path), 0, ctypes.byref(stream_data), 0)
        if handle == invalid_handle:
            error = ctypes.get_last_error()
            if error in unsupported_errors or error == error_handle_eof:
                continue
            raise ctypes.WinError(error)
        try:
            while True:
                stream_name = stream_data.cStreamName
                if stream_name.casefold() != "::$data":
                    raise ValueError(
                        f"Alternate data streams are not permitted in {description}: "
                        f"{path} ({stream_name})"
                    )
                if not find_next(handle, ctypes.byref(stream_data)):
                    error = ctypes.get_last_error()
                    if error != error_handle_eof:
                        raise ctypes.WinError(error)
                    break
        finally:
            find_close(handle)


def _validated_relative_path(raw_path: str) -> tuple[PurePosixPath, str]:
    """Validate a manifest path for both POSIX and Windows extraction semantics."""
    if not raw_path or "\\" in raw_path or "\x00" in raw_path:
        raise ValueError(f"Unsafe FFmpeg notice path in manifest: {raw_path!r}")

    posix = PurePosixPath(raw_path)
    windows = PureWindowsPath(raw_path)
    if (
        posix.is_absolute()
        or windows.is_absolute()
        or windows.drive
        or windows.root
        or posix.as_posix() != raw_path
        or not posix.parts
    ):
        raise ValueError(f"Unsafe FFmpeg notice path in manifest: {raw_path!r}")

    reserved = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$", "CLOCK$"}
    for part in posix.parts:
        if part in {"", ".", ".."} or ":" in part or part.endswith((" ", ".")):
            raise ValueError(f"Unsafe FFmpeg notice path in manifest: {raw_path!r}")
        stem = part.split(".", 1)[0].upper()
        if stem in reserved or re.fullmatch(r"(?:COM|LPT)(?:[1-9]|[¹²³])", stem):
            raise ValueError(f"Windows-reserved FFmpeg notice path in manifest: {raw_path!r}")

    return posix, posix.as_posix()


def import_notices(source_package: Path, licenses_dir: Path) -> dict[str, Any]:
    source_package = source_package.resolve(strict=True)
    source_doc = source_package / "doc"
    source_license = source_package / "LICENSE.txt"
    if source_doc.is_symlink() or source_license.is_symlink():
        raise ValueError("FFmpeg package doc/ and LICENSE.txt must not be symlinks")
    if not source_doc.is_dir():
        raise ValueError(f"FFmpeg package documentation folder is missing: {source_doc}")
    if not source_license.is_file():
        raise ValueError(f"FFmpeg package LICENSE.txt is missing: {source_license}")
    _reject_symlinks(source_doc, "FFmpeg source documentation bundle")
    _reject_alternate_data_streams(source_doc, "FFmpeg source documentation bundle")
    _reject_alternate_data_streams(source_license, "FFmpeg source license file")

    files = sorted(p for p in source_doc.rglob("*") if p.is_file())
    if not files:
        raise ValueError(f"FFmpeg documentation/notices folder is empty: {source_doc}")
    validated_names: set[str] = set()
    for source_path in sorted(source_doc.rglob("*")):
        relative = source_path.relative_to(source_doc).as_posix()
        _, normalized = _validated_relative_path(relative)
        folded = normalized.casefold()
        if folded in validated_names:
            raise ValueError(f"Windows-colliding FFmpeg notice path: {normalized}")
        validated_names.add(folded)
        if source_path.is_file() and folded == "manifest.json":
            raise ValueError("FFmpeg source documentation cannot contain a root MANIFEST.json file")

    licenses_dir.mkdir(parents=True, exist_ok=True)
    licenses_dir = licenses_dir.resolve()
    destination = licenses_dir / "FFMPEG_DEPENDENCY_NOTICES"
    license_destination = licenses_dir / "FFMPEG_LICENSE.txt"
    if destination.is_symlink() or license_destination.is_symlink():
        raise ValueError("Existing FFmpeg notice destination and license file must not be symlinks")
    if destination.exists() and not destination.is_dir():
        raise ValueError(f"FFmpeg notice destination is not a directory: {destination}")
    if license_destination.exists() and not license_destination.is_file():
        raise ValueError(f"FFmpeg license destination is not a regular file: {license_destination}")

    # Build and verify the complete new bundle away from the live destination.
    # A failed copy/hash/manifest/verification must never destroy a previously
    # imported license set.
    with tempfile.TemporaryDirectory(prefix=".ffmpeg-notices-stage-", dir=licenses_dir) as stage_name:
        stage_root = Path(stage_name)
        staged_destination = stage_root / destination.name
        staged_license = stage_root / license_destination.name
        shutil.copytree(source_doc, staged_destination)
        shutil.copy2(source_license, staged_license)
        _reject_symlinks(staged_destination, "staged FFmpeg documentation bundle")
        _reject_alternate_data_streams(staged_destination, "staged FFmpeg documentation bundle")
        _reject_alternate_data_streams(staged_license, "staged FFmpeg source license file")

        entries = []
        for copied in sorted(p for p in staged_destination.rglob("*") if p.is_file()):
            relative = copied.relative_to(staged_destination).as_posix()
            entries.append({"path": relative, "bytes": copied.stat().st_size, "sha256": sha256(copied)})

        manifest: dict[str, Any] = {
            "schema_version": 1,
            "source_package_folder": source_package.name,
            "files": entries,
        }
        manifest_path = staged_destination / "MANIFEST.json"
        # This write is inside an isolated staging directory; it is not visible
        # to consumers until the fully verified directory is committed below.
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        verify_notices(stage_root)

        backup_root = Path(tempfile.mkdtemp(prefix=".ffmpeg-notices-backup-", dir=licenses_dir))
        pairs = ((staged_destination, destination), (staged_license, license_destination))
        backups: list[tuple[Path, Path]] = []
        installed: list[Path] = []
        try:
            for _staged, target in pairs:
                if target.exists():
                    backup = backup_root / target.name
                    os.replace(target, backup)
                    backups.append((backup, target))
            for staged, target in pairs:
                os.replace(staged, target)
                installed.append(target)
        except BaseException as commit_error:
            rollback_errors: list[str] = []
            for target in reversed(installed):
                try:
                    if target.is_dir() and not target.is_symlink():
                        shutil.rmtree(target)
                    else:
                        target.unlink(missing_ok=True)
                except OSError as exc:
                    rollback_errors.append(f"remove {target}: {exc}")
            for backup, target in reversed(backups):
                try:
                    os.replace(backup, target)
                except OSError as exc:
                    rollback_errors.append(f"restore {target}: {exc}")
            if rollback_errors:
                raise RuntimeError(
                    "FFmpeg notice import failed and rollback was incomplete; "
                    f"preserved backup at {backup_root}. Errors: {'; '.join(rollback_errors)}"
                ) from commit_error
            shutil.rmtree(backup_root, ignore_errors=True)
            raise
        else:
            shutil.rmtree(backup_root)

    return manifest


def verify_notices(licenses_dir: Path) -> dict[str, Any]:
    licenses_dir = licenses_dir.resolve()
    directory = licenses_dir / "FFMPEG_DEPENDENCY_NOTICES"
    manifest_path = directory / "MANIFEST.json"
    license_file = licenses_dir / "FFMPEG_LICENSE.txt"

    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f"FFmpeg dependency notice directory is missing or unsafe: {directory}")
    if manifest_path.is_symlink():
        raise ValueError(f"FFmpeg notice manifest must not be a symlink: {manifest_path}")
    if not manifest_path.is_file():
        raise ValueError(f"FFmpeg dependency notice manifest is missing: {manifest_path}")
    _reject_symlinks(directory, "FFmpeg documentation bundle")
    _reject_alternate_data_streams(directory, "FFmpeg documentation bundle")
    if license_file.is_symlink():
        raise ValueError(f"FFMPEG_LICENSE.txt must not be a symlink: {license_file}")
    if not license_file.is_file() or license_file.stat().st_size == 0:
        raise ValueError("FFMPEG_LICENSE.txt is missing or empty")
    _reject_alternate_data_streams(license_file, "FFmpeg license file")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read FFmpeg notice manifest: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ValueError("FFmpeg notice manifest root must be a JSON object")
    schema_version = manifest.get("schema_version")
    if type(schema_version) is not int or schema_version != 1 or not isinstance(manifest.get("files"), list) or not manifest["files"]:
        raise ValueError("FFmpeg notice manifest schema is invalid or empty")

    expected: set[str] = set()
    expected_windows: set[str] = set()
    validated_entries: list[tuple[dict[str, Any], PurePosixPath, str]] = []
    for entry in manifest["files"]:
        if not isinstance(entry, dict):
            raise ValueError("FFmpeg notice manifest entries must be JSON objects")
        rel = entry.get("path", "")
        if not isinstance(rel, str):
            raise ValueError("FFmpeg notice manifest path must be a string")
        pure, rel_norm = _validated_relative_path(rel)
        windows_norm = rel_norm.casefold()
        if rel_norm in expected or windows_norm in expected_windows:
            raise ValueError(f"Duplicate or Windows-colliding FFmpeg notice path in manifest: {rel_norm}")
        expected.add(rel_norm)
        expected_windows.add(windows_norm)
        validated_entries.append((entry, pure, rel_norm))

    # Validate the entire manifest's path namespace before opening any listed file.
    for entry, pure, rel_norm in validated_entries:
        target = directory.joinpath(*pure.parts)
        try:
            target.resolve(strict=True).relative_to(directory.resolve(strict=True))
        except (OSError, ValueError) as exc:
            raise ValueError(f"FFmpeg notice path escapes its directory or is missing: {rel_norm}") from exc
        if not target.is_file():
            raise ValueError(f"FFmpeg license/dependency notice is missing: {rel_norm}")
        expected_size = entry.get("bytes", -1)
        if type(expected_size) is not int or expected_size < 0:
            raise ValueError(f"Invalid FFmpeg notice byte count: {rel_norm}")
        if target.stat().st_size != expected_size:
            raise ValueError(f"FFmpeg notice size mismatch: {rel_norm}")
        digest = entry.get("sha256", "")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            raise ValueError(f"Invalid FFmpeg notice SHA-256 in manifest: {rel_norm}")
        if sha256(target) != digest.lower():
            raise ValueError(f"FFmpeg license/dependency notice SHA-256 mismatch: {rel_norm}")

    actual = {
        p.relative_to(directory).as_posix()
        for p in directory.rglob("*")
        if p.is_file() and p != manifest_path
    }
    if actual != expected:
        missing = sorted(expected - actual)
        unlisted = sorted(actual - expected)
        raise ValueError(f"FFmpeg notice set differs from manifest; missing={missing}, unlisted={unlisted}")

    return {"ok": True, "notice_files": len(expected), "notice_manifest": str(manifest_path)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    importer = sub.add_parser("import", help="copy doc/ and LICENSE.txt from an extracted FFmpeg package")
    importer.add_argument("--source-package", required=True, type=Path)
    importer.add_argument("--licenses-dir", type=Path, default=Path(__file__).resolve().parents[1] / "LICENSES")
    verifier = sub.add_parser("verify", help="verify every imported FFmpeg notice and its manifest")
    verifier.add_argument("--licenses-dir", type=Path, default=Path(__file__).resolve().parents[1] / "LICENSES")
    args = parser.parse_args(argv)
    try:
        if args.command == "import":
            result = import_notices(args.source_package, args.licenses_dir)
            print(json.dumps({"ok": True, "notice_files": len(result["files"]), "manifest": str(args.licenses_dir / "FFMPEG_DEPENDENCY_NOTICES" / "MANIFEST.json")}, indent=2))
        else:
            print(json.dumps(verify_notices(args.licenses_dir), indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FFmpeg notice check failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
