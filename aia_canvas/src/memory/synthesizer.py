"""Living memory background distillation worker."""

from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Callable, Optional

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
    
    MIN_UNCOMPACTED_TURNS = 3

    def __init__(
        self,
        event_ledger: Optional[EventLedger] = None,
        profile_manager: Optional[ProfileManager] = None,
        idle_threshold_s: float = 300.0,
        parent: Optional[QObject] = None,
        llm_distiller: Optional[Callable[[list[dict]], dict[str, Any]]] = None,
        memory_db_path: Optional[str | Path] = None,
    ) -> None:
        super().__init__(parent)
        self.llm_distiller = llm_distiller
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

        if memory_db_path:
            self.memory_db_path = Path(memory_db_path)
        else:
            local_path = Path("memory.db")
            if local_path.exists():
                self.memory_db_path = local_path
            else:
                self.memory_db_path = Path.home() / ".local" / "share" / "aether" / "memory.db"

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

    def _is_substantive_topic(self, text: str) -> bool:
        """Check if a topic is substantive (not trivial)."""
        if not text:
            return False
        clean = text.strip()
        words = clean.split()
        if len(words) <= 3:
            return False
        lower_text = clean.lower()
        prefixes = (
            "hello ", "hi ", "hey ", "thanks ", "ok ",
            "what are ", "who are ", "can you "
        )
        if lower_text.startswith(prefixes):
            return False
        return True

    def _persist_to_memory_db(self, facts: dict[str, Any], session_summary: Optional[str], staged_nodes: list[dict[str, Any]]) -> dict[str, int]:
        stats = {"facts_persisted": 0, "episodes_created": 0, "file_refs_linked": 0}
        
        self.memory_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with sqlite3.connect(str(self.memory_db_path), timeout=5.0) as conn:
                conn.execute("PRAGMA journal_mode = WAL;")
                conn.execute("PRAGMA foreign_keys = ON;")
                
                # Ensure tables exist
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS facts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        category TEXT NOT NULL DEFAULT 'general', 
                        key TEXT UNIQUE NOT NULL, 
                        value TEXT NOT NULL, 
                        confidence REAL DEFAULT 1.0, 
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS episodes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        timestamp REAL NOT NULL, 
                        active_project TEXT DEFAULT '', 
                        summary TEXT NOT NULL, 
                        turn_count INTEGER DEFAULT 0, 
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS episode_file_refs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        episode_id INTEGER NOT NULL, 
                        file_path TEXT NOT NULL, 
                        relation TEXT DEFAULT 'referenced', 
                        FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE
                    )
                ''')
                
                conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_key ON facts(key);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_episodes_timestamp ON episodes(timestamp);")
                
                # 1. Upsert facts
                for full_key, value in facts.items():
                    if "." in full_key:
                        parts = full_key.split(".", 1)
                        category, key = parts[0], parts[1]
                    else:
                        category, key = 'general', full_key
                        
                    conn.execute('''
                        INSERT INTO facts (category, key, value, updated_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(key) DO UPDATE SET 
                            value = excluded.value, 
                            updated_at = CURRENT_TIMESTAMP
                    ''', (category, key, str(value)))
                    stats["facts_persisted"] += 1
                
                # 2. Session summary and linking
                if session_summary:
                    active_project = self.profile_manager.get_working_state().get("active_project", "")
                    cursor = conn.execute('''
                        INSERT INTO episodes (timestamp, active_project, summary, turn_count)
                        VALUES (?, ?, ?, ?)
                    ''', (time.time(), active_project, session_summary, 0))
                    episode_id = cursor.lastrowid
                    
                    if episode_id:
                        stats["episodes_created"] += 1
                        
                        if staged_nodes:
                            for node in staged_nodes:
                                file_path = node.get("file_path") or str(node.get("title", ""))
                                if file_path and file_path != "None":
                                    conn.execute('''
                                        INSERT INTO episode_file_refs (episode_id, file_path, relation)
                                        VALUES (?, ?, 'referenced')
                                    ''', (episode_id, file_path))
                                    stats["file_refs_linked"] += 1
                                
                conn.commit()
        except sqlite3.Error as e:
            print(f"Error persisting to memory db: {e}")
            
        return stats


    def _extract_heuristics_from_text(self, text: str) -> dict[str, Any]:
        """Extract facts and active project updates from conversational text."""
        stats = {"facts_extracted": 0, "project_updated": False, "extracted_facts": {}}
        if not text:
            return stats
            
        # a) Active Project
        project_patterns = [
            r"(?:set|switch|change|current)\s+active\s+project\s+(?:to\s+)?['\"]?([^'\"\n\.]+)['\"]?",
            r"(?:working on|objective is)\s+['\"]?([^'\"\n\.]+)['\"]?"
        ]
        for p in project_patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                project = match.group(1).strip()
                self.profile_manager.update_active_project(project)
                stats["project_updated"] = True
                break

        # b) Explicit Facts
        fact_pattern = r"(?:remember that|note that|my)\s+([a-zA-Z0-9_\-\s]+?)\s+(?:is|are|=|:)\s+['\"]?([^'\"\n\.]+)['\"]?"
        known_categories = ["entities", "system_environment", "collaboration_style"]
        
        for match in re.finditer(fact_pattern, text, re.IGNORECASE):
            raw_key = match.group(1).strip()
            clean_key = raw_key.lower().replace(' ', '_')
            clean_val = match.group(2).strip()
            
            nested = False
            for cat in known_categories:
                if clean_key.startswith(cat + "_"):
                    subkey = clean_key[len(cat) + 1:]
                    self.profile_manager.update_identity(cat, {subkey: clean_val})
                    stats["extracted_facts"][f"{cat}.{subkey}"] = clean_val
                    nested = True
                    break
            
            if not nested:
                self.profile_manager.update_identity(clean_key, clean_val)
                stats["extracted_facts"][clean_key] = clean_val
            stats["facts_extracted"] += 1
            
        return stats

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
            facts_extracted = 0
            touched_node_stubs: list[dict[str, Any]] = []
            all_facts: dict[str, Any] = {}

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
                            heuristics = self._extract_heuristics_from_text(clean_topic)
                            facts_extracted += heuristics.get("facts_extracted", 0)
                            all_facts.update(heuristics.get("extracted_facts", {}))
                            
                            if self._is_substantive_topic(clean_topic):
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
                            all_facts[str(fact_key)] = fact_value
                    elif "facts" in payload and isinstance(payload["facts"], dict):
                        for k, v in payload["facts"].items():
                            self.profile_manager.update_identity(str(k), v)
                            all_facts[str(k)] = v
                    elif "identity" in payload and isinstance(payload["identity"], dict):
                        for k, v in payload["identity"].items():
                            self.profile_manager.update_identity(str(k), v)
                            all_facts[str(k)] = v


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

            # Phase 2: Semantic Distillation
            semantic_distillation_performed = False
            omni_queries = [e for e in uncompacted if e.get("event_type") == "omni_query"]

            if self.llm_distiller is not None and len(omni_queries) >= self.MIN_UNCOMPACTED_TURNS:
                self._engine_state = "DISTILLING"
                self.engineStateChanged.emit("DISTILLING")
                
                try:
                    batch = []
                    for q in omni_queries:
                        payload = q.get("payload", {})
                        if isinstance(payload, str):
                            text = payload
                        else:
                            text = payload.get("query") or payload.get("topic") or payload.get("prompt") or ""
                        if text:
                            batch.append({"text": text, "timestamp": q.get("timestamp")})
                            
                    distillation_result = self.llm_distiller(batch)
                    
                    if distillation_result.get("active_project"):
                        self.profile_manager.update_active_project(distillation_result["active_project"])
                        
                    facts_learned = distillation_result.get("facts_learned")
                    if isinstance(facts_learned, dict):
                        for k, v in facts_learned.items():
                            self.profile_manager.update_identity(str(k), v)
                            all_facts[str(k)] = v
                            
                    facts_retracted = distillation_result.get("facts_retracted")
                    if isinstance(facts_retracted, list):
                        identity = self.profile_manager.get_identity()
                        modified = False
                        for k in facts_retracted:
                            if str(k) in identity:
                                del identity[str(k)]
                                modified = True
                        if modified:
                            self.profile_manager.save_identity(identity)
                            
                    semantic_distillation_performed = True
                except Exception:
                    pass

            # Update last compacted event id
            if uncompacted:
                self.last_compacted_event_id = max(e.get("id", 0) for e in uncompacted)

            # 5. Clean up expired TTL rows
            pruned_count = self.event_ledger.prune_events()
            
            working_state = self.profile_manager.get_working_state()
            session_summary_parts = []
            if working_state.get("active_project"):
                session_summary_parts.append(f"Active project: {working_state['active_project']}")
            if working_state.get("hot_topics"):
                session_summary_parts.append("Hot topics: " + ", ".join(working_state["hot_topics"][:5]))
            
            session_summary = " | ".join(session_summary_parts) if session_summary_parts else None
            memory_stats = self._persist_to_memory_db(all_facts, session_summary, touched_node_stubs)

            compaction_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self.compaction_ms = compaction_ms

            stats = {
                "events_processed": len(uncompacted),
                "hot_topics_added": hot_topics_added,
                "facts_extracted": facts_extracted,
                "pruned": pruned_count,
                "compaction_ms": compaction_ms,
                "semantic_distillation_performed": semantic_distillation_performed,
                "facts_persisted": memory_stats.get("facts_persisted", 0),
                "episodes_created": memory_stats.get("episodes_created", 0),
                "file_refs_linked": memory_stats.get("file_refs_linked", 0)
            }
            self.synthesized.emit(stats)
            return stats
        finally:
            self._engine_state = "LATENT"
            self.engineStateChanged.emit("LATENT")

    def check_idle_and_synthesize(self) -> Optional[dict[str, Any]]:
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

    def shutdown(self) -> dict[str, Any]:
        """Graceful shutdown hook stopping timer and executing final compaction pass."""
        self.stop()
        return self.synthesize_sync()

