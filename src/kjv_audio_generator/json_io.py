from __future__ import annotations

import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


@contextmanager
def atomic_output_path(path: str | Path) -> Iterator[Path]:
    """Yield a unique same-directory path and atomically commit it on success.

    Callers can let third-party writers (for example soundfile or torch.save)
    create the file. Once the writer closes it, this helper fsyncs the staged
    bytes and replaces the destination. Any exception preserves the previous
    destination and removes the staging file.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=f".tmp{target.suffix}", dir=str(target.parent)
    )
    temporary = Path(temporary_name)
    try:
        os.close(fd)
        fd = -1
        yield temporary
        if not temporary.is_file() or temporary.stat().st_size == 0:
            raise OSError(f"Atomic writer produced an empty staged output: {temporary}")
        with temporary.open("rb+") as handle:
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except BaseException:
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass
        temporary.unlink(missing_ok=True)
        raise


def write_json_atomic(path: str | Path, payload: Any) -> None:
    """Persist UTF-8 JSON through a unique same-directory temp and atomic replace."""
    # Serialize before creating any file so unsupported objects cannot leave
    # temporary artifacts or affect an existing destination.
    serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    with atomic_output_path(path) as temporary:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized)
            handle.flush()


def copy_file_atomic(source: str | Path, destination: str | Path) -> None:
    """Copy a completed file to a unique staging file, fsync, then atomically replace."""
    source_path = Path(source)
    if not source_path.is_file():
        raise FileNotFoundError(f"Atomic copy source is not a regular file: {source_path}")
    with atomic_output_path(destination) as temporary:
        with temporary.open("wb") as destination_handle, source_path.open("rb") as source_handle:
            shutil.copyfileobj(source_handle, destination_handle, length=1024 * 1024)
            destination_handle.flush()
