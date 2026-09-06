"""Living memory background distillation worker."""

from __future__ import annotations

import time
from typing import Any, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtProperty, pyqtSignal

try:
    from aia_canvas.src.memory.event_ledger import EventLedger
    from aia_canvas.src.memory.profile_manager import ProfileManager
except ModuleNotFoundError:
    from memory.event_ledger import EventLedger
    from memory.profile_manager import ProfileManager


class MemorySynthesizer(QObject):
    """Background distillation worker for living memory."""

    synthesized = pyqtSignal(dict)
    engineStateChanged = pyqtSignal(str)

    def __init__(
        self,
        event_ledger: Optional[EventLedger] = None,
        profile_manager: Optional[ProfileManager] = None,
        idle_threshold_s: float = 300.0,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.event_ledger: EventLedger = (
            event_ledger if event_ledger is not None else EventLedger()
        )
        self.profile_manager: ProfileManager = (
            profile_manager if profile_manager is not None else ProfileManager()
        )
        self.idle_threshold_s: float = float(idle_threshold_s)
        self.last_event_time: float = time.time()
        self.is_running: bool = False
        self.last_compacted_event_id: int = 0
        self._engine_state: str = "LATENT"
        self._timer: Optional[QTimer] = None
        self.compaction_ms: float = 0.0

    @pyqtProperty(str, notify=engineStateChanged)
    def engineState(self) -> str:
        return self._engine_state

    @property
    def last_processed_event_id(self) -> int:
        return self.last_compacted_event_id

    @last_processed_event_id.setter
    def last_processed_event_id(self, val: int) -> None:
        self.last_compacted_event_id = val

    def notify_event_occurred(self, *args: Any, **kwargs: Any) -> None:
        """Updates last_event_time to the current timestamp."""
        self.last_event_time = time.time()

    def has_uncompacted_events(self) -> bool:
        """Returns True if there are uncompacted events in the event ledger."""
        recent = self.event_ledger.get_recent_events(limit=1)
        if not recent:
            return False
        return recent[0].get("id", 0) > self.last_compacted_event_id

    def synthesize_sync(self) -> dict[str, Any]:
        """Deterministic distillation method running the compaction pass.

        1. Queries recent uncompacted events from event_ledger.get_recent_events(limit=250).
        2. Extracts topics from conversational queries (event_type == 'omni_query') and pushes them
           into profile_manager.push_hot_topic(topic).
        3. Gathers touched canvas nodes (event_type in ('select', 'dwell', 'pin')) and syncs recent
           node stubs into profile_manager.sync_staged_nodes(...).
        4. Checks for explicit identity facts in payloads (fact_key, fact_value) and persists them
           via profile_manager.update_identity(...).
        5. Calls event_ledger.prune_events() to clean up expired TTL rows.
        6. Returns dict summarizing compaction stats:
           {"events_processed": int, "hot_topics_added": int, "pruned": int, "compaction_ms": float}.
        """
        self._engine_state = "DISTILLING"
        self.engineStateChanged.emit("DISTILLING")
        start_time = time.perf_counter()
        try:
            recent_events = self.event_ledger.get_recent_events(limit=250)
            uncompacted = [e for e in recent_events if e.get("id", 0) > self.last_compacted_event_id]
            uncompacted.sort(key=lambda e: (e.get("timestamp", 0.0), e.get("id", 0)))

            hot_topics_added = 0
            touched_node_stubs: list[dict[str, Any]] = []

            for event in uncompacted:
                event_type = event.get("event_type", "")
                payload = event.get("payload")
                target_id = event.get("target_id", 0)
                archetype = event.get("archetype", "")

                # 2. Extract topics from conversational queries
                if event_type == "omni_query":
                    topic: Optional[str] = None
                    if isinstance(payload, dict):
                        topic = (
                            payload.get("topic")
                            or payload.get("query")
                            or payload.get("prompt")
                            or payload.get("text")
                        )
                    elif isinstance(payload, str) and payload.strip():
                        topic = payload.strip()

                    if topic and isinstance(topic, str):
                        clean_topic = topic.strip()
                        if clean_topic:
                            self.profile_manager.push_hot_topic(clean_topic)
                            hot_topics_added += 1

                # 3. Gather touched canvas nodes
                if event_type in ("select", "dwell", "pin", "selection"):
                    node_stub: dict[str, Any] = {}
                    if target_id:
                        node_stub["node_id"] = target_id
                        node_stub["target_id"] = target_id
                    if archetype:
                        node_stub["archetype"] = archetype
                    if isinstance(payload, dict):
                        node_stub.update(payload)
                        if "node_id" not in node_stub and "id" in payload:
                            node_stub["node_id"] = payload["id"]
                    if node_stub:
                        touched_node_stubs.append(node_stub)

                # 4. Check for explicit identity facts in payloads
                if isinstance(payload, dict):
                    if "fact_key" in payload and "fact_value" in payload:
                        fact_key = payload["fact_key"]
                        fact_value = payload["fact_value"]
                        if fact_key is not None:
                            self.profile_manager.update_identity(str(fact_key), fact_value)
                    elif "facts" in payload and isinstance(payload["facts"], dict):
                        for k, v in payload["facts"].items():
                            self.profile_manager.update_identity(str(k), v)
                    elif "identity" in payload and isinstance(payload["identity"], dict):
                        for k, v in payload["identity"].items():
                            self.profile_manager.update_identity(str(k), v)


            # Sync touched nodes into profile manager
            if touched_node_stubs:
                current_staged = list(self.profile_manager.get_working_state().get("staged_nodes", []))
                staged_map: dict[str, dict[str, Any]] = {}
                for n in current_staged:
                    if isinstance(n, dict):
                        key = n.get("node_id") or n.get("id") or n.get("target_id") or n.get("title")
                        staged_map[str(key) if key is not None else str(id(n))] = n
                    else:
                        staged_map[str(n)] = {"title": str(n)}

                for n in touched_node_stubs:
                    key = n.get("node_id") or n.get("id") or n.get("target_id") or n.get("title")
                    k_str = str(key) if key is not None else str(id(n))
                    if k_str in staged_map and isinstance(staged_map[k_str], dict):
                        merged = dict(staged_map[k_str])
                        merged.update(n)
                        staged_map.pop(k_str)
                        staged_map[k_str] = merged
                    else:
                        staged_map[k_str] = n

                self.profile_manager.sync_staged_nodes(list(staged_map.values()))

            # Update last compacted event id
            if uncompacted:
                self.last_compacted_event_id = max(e.get("id", 0) for e in uncompacted)

            # 5. Clean up expired TTL rows
            pruned_count = self.event_ledger.prune_events()

            compaction_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self.compaction_ms = compaction_ms

            stats = {
                "events_processed": len(uncompacted),
                "hot_topics_added": hot_topics_added,
                "pruned": pruned_count,
                "compaction_ms": compaction_ms,
            }
            self.synthesized.emit(stats)
            return stats
        finally:
            self._engine_state = "LATENT"
            self.engineStateChanged.emit("LATENT")

    def check_idle_and_synthesize(self) -> Optional[dict[str, int]]:
        """Checks if idle threshold has elapsed and uncompacted events exist, triggering compaction."""
        now = time.time()
        if (now - self.last_event_time) >= self.idle_threshold_s:
            if self.has_uncompacted_events():
                return self.synthesize_sync()
        return None

    def _on_timer_tick(self) -> None:
        if not self.is_running:
            return
        self.check_idle_and_synthesize()

    def start(self, check_interval_ms: int = 30000) -> None:
        """Starts background idle monitoring."""
        self.is_running = True
        if self._timer is None:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._on_timer_tick)
        self._timer.setInterval(check_interval_ms)
        self._timer.start()

    def stop(self) -> None:
        """Stops background idle monitoring."""
        self.is_running = False
        if self._timer is not None and self._timer.isActive():
            self._timer.stop()

    def shutdown(self) -> dict[str, int]:
        """Graceful shutdown hook stopping timer and executing final compaction pass."""
        self.stop()
        return self.synthesize_sync()

