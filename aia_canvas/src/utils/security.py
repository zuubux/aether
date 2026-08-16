"""
Aether Canvas - Security & Sanitization
Enforces POSIX boundaries, path canonicalization, and safe subprocess execution.
"""

import os
from pathlib import Path
from typing import Optional

# Only allow paths inside the user's home directory or their temporary runtime dir
ALLOWED_PREFIXES = (str(Path.home()), f"/run/user/{os.getuid()}")

def canonicalize_safe_path(raw_path: str) -> Optional[Path]:
    """
    Resolves a path to its absolute physical location and verifies it falls
    within allowed secure boundaries. Prevents directory traversal.
    """
    try:
        if not raw_path:
            return None
            
        path = Path(raw_path).resolve(strict=False)
        path_str = str(path)
        
        for prefix in ALLOWED_PREFIXES:
            if path_str.startswith(prefix):
                return path
        return None
    except Exception:
        return None