"""
core/version.py — Read build info from the bundled version.txt.

version.txt format (written at build time):
  Built: 2026-02-25 18:22 EST
  Archive: 2026-02-25_1822_PyCronVideoAlarm_Linux

Returns safe fallbacks when running from source.
"""

import os
import sys

_BUILD_VERSION = None
_ARCHIVE_NAME = None


def _read_version_file() -> dict:
    global _BUILD_VERSION, _ARCHIVE_NAME
    if _BUILD_VERSION is not None:
        return {"version": _BUILD_VERSION, "archive": _ARCHIVE_NAME}

    candidates = []
    if getattr(sys, 'frozen', False):
        candidates.append(os.path.join(os.path.dirname(sys.executable), "version.txt"))
        if hasattr(sys, '_MEIPASS'):
            candidates.append(os.path.join(sys._MEIPASS, "version.txt"))
    candidates.append(os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "version.txt")
    ))

    for path in candidates:
        try:
            with open(path, "r") as f:
                lines = f.read().splitlines()
            data = {}
            for line in lines:
                if line.startswith("Built:"):
                    data["version"] = line.strip()
                elif line.startswith("Archive:"):
                    data["archive"] = line[len("Archive:"):].strip()
            _BUILD_VERSION = data.get("version", "Dev Build")
            _ARCHIVE_NAME = data.get("archive", None)
            return {"version": _BUILD_VERSION, "archive": _ARCHIVE_NAME}
        except FileNotFoundError:
            continue
        except Exception:
            continue

    _BUILD_VERSION = "Dev Build"
    _ARCHIVE_NAME = None
    return {"version": _BUILD_VERSION, "archive": None}


def get_build_version() -> str:
    return _read_version_file()["version"]


def get_archive_name() -> str | None:
    """Return pre-baked archive name, e.g. '2026-02-25_1822_PyCronVideoAlarm_Linux'. None in dev mode."""
    return _read_version_file()["archive"]
