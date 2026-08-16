import asyncio
import logging
from pathlib import Path
from watchfiles import awatch, Change

logger = logging.getLogger("aia_weaver.watcher")


class FileWatcher:
    def __init__(self, target_dirs: list[str], event_queue: asyncio.Queue):
        self.target_dirs = [Path(d).expanduser() for d in target_dirs]
        self.event_queue = event_queue

    async def watch_loop(self) -> None:
        """Monitors target directories using kernel-level async notifications."""
        valid_paths = []
        for p in self.target_dirs:
            if p.exists() and p.is_dir():
                valid_paths.append(p)
                logger.info(f"Sentinel active on target directory: {p.resolve()}")
            else:
                logger.warning(f"Target directory invalid or missing: {p}")

        if not valid_paths:
            logger.error("No valid target directories found. Watcher exiting.")
            return

        try:
            async for changes in awatch(*valid_paths):
                for change_type, file_path in changes:
                    action = self._map_change_type(change_type)

                    if self._should_ignore(file_path):
                        continue

                    event_data = {
                        "action": action,
                        "file_path": file_path,
                        "timestamp": asyncio.get_running_loop().time(),
                    }

                    await self.event_queue.put(event_data)
                    logger.info(f"Detected [{action.upper()}] -> {file_path}")

        except asyncio.CancelledError:
            logger.info("File watcher task cancelled.")
        except Exception as e:
            logger.error(f"Error in file watcher loop: {e}", exc_info=True)

    def _map_change_type(self, change: Change) -> str:
        if change == Change.added:
            return "created"
        elif change == Change.modified:
            return "modified"
        elif change == Change.deleted:
            return "deleted"
        return "unknown"

    def _should_ignore(self, file_path_str: str) -> bool:
        """Filters out binary noise, metadata, and sensitive secret files."""
        path = Path(file_path_str)
        parts = path.parts
        name_lower = path.name.lower()

        # 1. Ignore common build/metadata/security directories
        ignore_dirs = {
            ".git", "__pycache__", ".venv", "node_modules", 
            "target", ".aws", ".ssh", ".gnupg", ".config"
        }
        if any(d in parts for d in ignore_dirs):
            return True

        # 2. Strict Security Denylist: Never ingest secrets or private key extensions
        sensitive_extensions = {
            ".pem", ".key", ".p12", ".pfx", ".crt", ".keystore",
            ".kdbx", ".env", ".asc", ".sig"
        }
        if path.suffix.lower() in sensitive_extensions:
            logger.warning(f"Security Filter: Blocked sensitive extension -> {path.name}")
            return True

        # 3. Block known sensitive credential filenames
        sensitive_filenames = {
            "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa",
            "credentials", "shadow", "passwd", "authorized_keys",
            "known_hosts", ".bash_history", ".zsh_history"
        }
        if name_lower in sensitive_filenames:
            logger.warning(f"Security Filter: Blocked sensitive file -> {path.name}")
            return True

        # 4. Ignore hidden and temp swap files
        if path.name.startswith(".") or path.name.endswith((".swp", ".tmp", "~")):
            return True

        return False