from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

from kjv_audio_generator.__main__ import main


def _record_entrypoint_diagnostics(
    stage: str,
    *,
    exit_code: int | None = None,
    error: str | None = None,
) -> None:
    """Write opt-in frozen-launch diagnostics without relying on console streams."""
    target = os.environ.get("KJV_APP_DIAGNOSTICS_FILE")
    if not target:
        return
    try:
        destination = Path(target)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "stage": stage,
            "argv": list(sys.argv),
            "executable": sys.executable,
            "cwd": os.getcwd(),
            "frozen": bool(getattr(sys, "frozen", False)),
            "stdout_is_none": sys.stdout is None,
            "stderr_is_none": sys.stderr is None,
            "exit_code": exit_code,
            "error": error,
        }
        serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        temporary = destination.with_name(destination.name + ".tmp")
        temporary.write_text(serialized, encoding="utf-8")
        os.replace(temporary, destination)
    except Exception:
        # Diagnostics must never block normal app launch or change its exit code.
        pass


_record_entrypoint_diagnostics("started")
try:
    _exit_code = main()
except BaseException:
    _record_entrypoint_diagnostics("exception", error=traceback.format_exc())
    raise
else:
    _record_entrypoint_diagnostics("completed", exit_code=int(_exit_code or 0))
    raise SystemExit(_exit_code)
