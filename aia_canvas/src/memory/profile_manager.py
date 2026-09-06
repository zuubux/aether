"""Living memory profile manager for Aether."""

import copy
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_IDENTITY: dict[str, Any] = {
    "entities": {},
    "system_environment": {
        "os": "Linux",
        "desktop_layout": "spatial_canvas",
        "hardware_constraints": {},
    },
    "collaboration_style": {
        "tone": "direct_authentic_peer",
        "conciseness": "high",
        "structural_scaffolding": True,
    },
}

DEFAULT_WORKING_STATE: dict[str, Any] = {
    "active_project": "",
    "hot_topics": [],
    "staged_nodes": [],
}


class ProfileManager:
    """Manages identity and working state profile configurations."""

    def __init__(self, config_dir: str | Path | None = None) -> None:
        if config_dir is not None:
            self.config_dir = Path(config_dir).expanduser().resolve()
        else:
            self.config_dir = Path.home() / ".config" / "aether"

        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.identity_path = self.config_dir / "identity.json"
        self.working_state_path = self.config_dir / "working_state.json"

        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        """Seed default configuration files if they do not exist."""
        if not self.identity_path.exists():
            self._atomic_save_json(self.identity_path, DEFAULT_IDENTITY)
        if not self.working_state_path.exists():
            self._atomic_save_json(self.working_state_path, DEFAULT_WORKING_STATE)

    def _load_json(self, file_path: Path, default_data: dict[str, Any]) -> dict[str, Any]:
        """Load JSON from disk, seeding defaults if missing or corrupted."""
        if not file_path.exists():
            self._atomic_save_json(file_path, default_data)
            return copy.deepcopy(default_data)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return copy.deepcopy(default_data)

    def _atomic_save_json(self, file_path: Path, data: dict[str, Any]) -> None:
        """Atomically save JSON data using a temporary file and replace."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        temp_file = file_path.with_name(f"{file_path.name}.{os.getpid()}.tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_file, file_path)
        except BaseException:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass
            raise

    def get_identity(self) -> dict[str, Any]:
        """Retrieve the identity profile."""
        return self._load_json(self.identity_path, DEFAULT_IDENTITY)

    def save_identity(self, data: dict[str, Any]) -> None:
        """Save the identity profile."""
        self._atomic_save_json(self.identity_path, data)

    def update_identity(self, key: str, val: Any) -> None:
        """Merge or add a key at the top level of identity."""
        data = self.get_identity()
        if isinstance(data.get(key), dict) and isinstance(val, dict):
            data[key].update(val)
        else:
            data[key] = val
        self.save_identity(data)

    def get_working_state(self) -> dict[str, Any]:
        """Retrieve the current working state."""
        return self._load_json(self.working_state_path, DEFAULT_WORKING_STATE)

    def save_working_state(self, data: dict[str, Any]) -> None:
        """Save the working state."""
        self._atomic_save_json(self.working_state_path, data)

    def update_active_project(self, project: str) -> None:
        """Update the active project name."""
        state = self.get_working_state()
        state["active_project"] = project
        self.save_working_state(state)

    def push_hot_topic(self, topic: str, max_topics: int = 5) -> None:
        """Push topic to hot_topics, deduplicating and capping length with FIFO eviction."""
        state = self.get_working_state()
        hot_topics: list[str] = state.get("hot_topics", [])

        if topic in hot_topics:
            hot_topics.remove(topic)

        hot_topics.append(topic)

        if len(hot_topics) > max_topics:
            hot_topics = hot_topics[-max_topics:]

        state["hot_topics"] = hot_topics
        self.save_working_state(state)

    def sync_staged_nodes(self, nodes: list[dict[str, Any]]) -> None:
        """Synchronize staged nodes with the provided snapshot list."""
        state = self.get_working_state()
        state["staged_nodes"] = copy.deepcopy(nodes)
        self.save_working_state(state)
