# utils/security.py
import logging
from pathlib import Path

logger = logging.getLogger("aia_weaver.security")


def is_safe_path(requested_path_str: str, allowed_directories: list[Path]) -> bool:
    """
    Canonicalizes input paths and verifies that the target path falls 
    strictly inside at least one allowed root directory boundary.
    """
    if not requested_path_str:
        return False

    try:
        # Resolve symlinks, dot-dots (..), and relative components
        target_path = Path(requested_path_str).expanduser().resolve()

        for allowed_dir in allowed_directories:
            allowed_root = allowed_dir.expanduser().resolve()

            # Check if target is the root itself or a descendant child
            if target_path == allowed_root or allowed_root in target_path.parents:
                return True

        logger.warning(
            f"Path Traversal Guard: Blocked attempt to access out-of-bounds path -> {target_path}"
        )
        return False

    except Exception as e:
        logger.error(f"Error validating path '{requested_path_str}': {e}")
        return False