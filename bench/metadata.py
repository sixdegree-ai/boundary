"""Run metadata collected automatically for every benchmark result."""

import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any


def collect() -> dict[str, Any]:
    """Collect environment and run metadata."""
    meta: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "boundary_version": _get_version(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "git_commit": _git("rev-parse", "--short", "HEAD"),
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_dirty": _git("status", "--porcelain") != "",
    }
    return meta


def _get_version() -> str:
    try:
        from importlib.metadata import version

        return version("boundary")
    except Exception:
        return "unknown"


def _git(*args: str) -> str | bool:
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=os.path.dirname(os.path.dirname(__file__)),
        )
        if result.returncode != 0:
            return ""
        return result.stdout.strip()
    except Exception:
        return ""
