import os
import subprocess
from utils.security import canonicalize_safe_path

def open_in_file_manager(file_path: str):
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

def open_in_external_editor(file_path: str):
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
