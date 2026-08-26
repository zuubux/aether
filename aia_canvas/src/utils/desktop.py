"""
Desktop Utilities Module
Provides decoupled Linux desktop integration handlers for launching external file managers
and default desktop applications via xdg-open in independent sub-sessions.
"""

import os
import subprocess
from pathlib import Path
from typing import Union

from utils.security import canonicalize_safe_path


def open_in_file_manager(file_path: Union[str, Path]) -> bool:
    """Open the parent directory of a file or target directory in system file manager.

    Launches `xdg-open` in a detached session without blocking Qt main event loop or
    coupling to desktop environment particulars.

    Args:
        file_path: Target file path or directory path.

    Returns:
        bool: True if process was spawned successfully, False if target path is invalid.
    """
    safe_path = canonicalize_safe_path(file_path)
    if not safe_path:
        return False
    target_dir = safe_path if safe_path.is_dir() else safe_path.parent
    if target_dir.exists():
        target_path_str = os.path.realpath(str(target_dir))
        subprocess.Popen(
            ["xdg-open", target_path_str],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            shell=False,
        )
        return True
    return False


def open_in_external_editor(file_path: Union[str, Path]) -> bool:
    """Open a target file in system default external editor/viewer.

    Launches `xdg-open` in a detached session, ensuring decoupled desktop execution
    without blocking application state.

    Args:
        file_path: Target file path to open.

    Returns:
        bool: True if process was spawned successfully, False if target path is missing.
    """
    safe_path = canonicalize_safe_path(file_path)
    if not safe_path:
        return False
    if safe_path.exists():
        target_path_str = os.path.realpath(str(safe_path))
        subprocess.Popen(
            ["xdg-open", target_path_str],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            shell=False,
        )
        return True
    return False
