import os
import sys

def get_project_root():
    """
    Determine the project root directory.
    Handles:
    1. PyInstaller frozen application (sys._MEIPASS or executable dir)
    2. Development environment (src/core/utils.py -> project root is 2 levels up)
    """
    if getattr(sys, 'frozen', False):
        # Frozen: executable lives in dist/ or alongside sequences/
        # Use the directory containing the executable, NOT sys._MEIPASS for writing files
        return os.path.dirname(os.path.abspath(sys.executable))
    else:
        # Development: src/core/utils.py -> project root is two levels up
        # src/core/utils.py -> src/core -> src -> root
        return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

def get_signal_file_path():
    """
    Get the absolute path to the 'kill_overlay.signal' file in the project root.
    """
    return os.path.join(get_project_root(), "kill_overlay.signal")
