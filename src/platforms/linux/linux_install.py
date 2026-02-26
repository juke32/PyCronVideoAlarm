"""
linux_install.py — Register PyCronVideoAlarm with the Linux desktop.

Called manually by the user via the Settings → "Add to Applications" button.
Creates a .desktop entry and installs the icon so the app appears in app
launchers and file managers with the correct icon.
"""

import os
import sys
import shutil
import logging
import subprocess

log = logging.getLogger(__name__)

APP_NAME        = "PyCron Video Alarm"
DESKTOP_ID      = "pycronvideoalarm"
ICON_FILENAME   = "alarm_icon7.png"

ICON_DIR        = os.path.expanduser("~/.local/share/icons")
DESKTOP_DIR     = os.path.expanduser("~/.local/share/applications")
ICON_DEST       = os.path.join(ICON_DIR, f"{DESKTOP_ID}.png")
DESKTOP_DEST    = os.path.join(DESKTOP_DIR, f"{APP_NAME}.desktop")


def _get_exe_path() -> str:
    return os.path.abspath(sys.executable)


def _get_bundle_icon() -> str | None:
    """Return path to the bundled icon PNG, or None if not found."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidate = os.path.join(meipass, ICON_FILENAME)
        if os.path.exists(candidate):
            return candidate
    # Fallback: icon alongside the executable
    candidate = os.path.join(os.path.dirname(_get_exe_path()), ICON_FILENAME)
    if os.path.exists(candidate):
        return candidate
    return None


def _write_desktop_file(exe_path: str):
    os.makedirs(DESKTOP_DIR, exist_ok=True)
    content = (
        "[Desktop Entry]\n"
        "Version=1.0\n"
        f"Name={APP_NAME}\n"
        "Comment=Video-based alarm clock with cron scheduling\n"
        f"Exec={exe_path}\n"
        f"Icon={ICON_DEST}\n"
        "Terminal=false\n"
        "Type=Application\n"
        "Categories=Utility;Alarm;\n"
        f"StartupWMClass={APP_NAME}\n"
    )
    with open(DESKTOP_DEST, "w") as f:
        f.write(content)
    os.chmod(DESKTOP_DEST, 0o755)
    log.info(f"Desktop entry written: {DESKTOP_DEST}")


def _copy_icon(src: str):
    os.makedirs(ICON_DIR, exist_ok=True)
    shutil.copy2(src, ICON_DEST)
    log.info(f"Icon installed: {ICON_DEST}")


def _refresh_desktop():
    try:
        subprocess.run(
            ["update-desktop-database", DESKTOP_DIR],
            check=False, capture_output=True, timeout=5
        )
    except Exception:
        pass


def install() -> tuple[bool, str]:
    """
    Register the app with the Linux desktop.
    Returns (success: bool, message: str).
    """
    exe_path = _get_exe_path()
    icon_src = _get_bundle_icon()

    if icon_src is None:
        return False, f"Icon file '{ICON_FILENAME}' not found next to the executable."

    try:
        _copy_icon(icon_src)
        _write_desktop_file(exe_path)
        _refresh_desktop()
        return True, (
            f"Added to Applications!\n\n"
            f"Icon: {ICON_DEST}\n"
            f"Desktop entry: {DESKTOP_DEST}\n\n"
            f"The app should now appear in your application launcher."
        )
    except Exception as e:
        log.error(f"Desktop registration failed: {e}")
        return False, f"Registration failed: {e}"


def is_registered() -> bool:
    """Return True if a .desktop entry already exists for this exe."""
    if not os.path.exists(DESKTOP_DEST):
        return False
    try:
        with open(DESKTOP_DEST) as f:
            return _get_exe_path() in f.read()
    except Exception:
        return False
