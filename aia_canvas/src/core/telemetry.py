"""
Aether Core Telemetry
High-precision TelemetrySink tracking engine & pipeline performance metrics.
"""

import collections
import time
from typing import Dict, Optional


class TelemetrySink:
    """Telemetry collector using high-resolution time.perf_counter_ns() with rolling deques (maxlen=60)."""

    _instance: Optional['TelemetrySink'] = None

    def __new__(cls) -> 'TelemetrySink':
        if cls._instance is None:
            cls._instance = super(TelemetrySink, cls).__new__(cls)
            cls._instance._init_state()
        return cls._instance

    @classmethod
    def instance(cls) -> 'TelemetrySink':
        return cls()

    def _init_state(self) -> None:
        self.physics_step_deques = collections.deque(maxlen=60)
        self.render_fps_deques = collections.deque(maxlen=60)
        self.ipc_rtt_deques = collections.deque(maxlen=60)
        self.db_query_deques = collections.deque(maxlen=60)
        self.llm_ttft_deques = collections.deque(maxlen=60)

    def reset(self) -> None:
        """Clear all metric ring buffers."""
        self.physics_step_deques.clear()
        self.render_fps_deques.clear()
        self.ipc_rtt_deques.clear()
        self.db_query_deques.clear()
        self.llm_ttft_deques.clear()

    def record_physics_step(self, val_ms: float) -> None:
        self.physics_step_deques.append(float(val_ms))

    def record_render_fps(self, fps: float) -> None:
        self.render_fps_deques.append(float(fps))

    def record_ipc_rtt(self, val_ms: float) -> None:
        self.ipc_rtt_deques.append(float(val_ms))

    def record_db_query(self, val_ms: float) -> None:
        self.db_query_deques.append(float(val_ms))

    def record_llm_ttft(self, val_ms: float) -> None:
        self.llm_ttft_deques.append(float(val_ms))

    def time_ns(self) -> int:
        return time.perf_counter_ns()

    def calc_ns_to_ms(self, start_ns: int, end_ns: Optional[int] = None) -> float:
        if end_ns is None:
            end_ns = time.perf_counter_ns()
        return (end_ns - start_ns) / 1e6

    @property
    def physics_step_ms(self) -> float:
        return self.physics_step_deques[-1] if self.physics_step_deques else 0.0

    @property
    def render_fps(self) -> float:
        return self.render_fps_deques[-1] if self.render_fps_deques else 120.0

    @property
    def ipc_rtt_ms(self) -> float:
        return self.ipc_rtt_deques[-1] if self.ipc_rtt_deques else 0.0

    @property
    def db_query_ms(self) -> float:
        return self.db_query_deques[-1] if self.db_query_deques else 0.0

    @property
    def llm_ttft_ms(self) -> float:
        return self.llm_ttft_deques[-1] if self.llm_ttft_deques else 0.0

    def get_snapshot(self) -> Dict[str, float]:
        return {
            "physics_step_ms": self.physics_step_ms,
            "render_fps": self.render_fps,
            "ipc_rtt_ms": self.ipc_rtt_ms,
            "db_query_ms": self.db_query_ms,
            "llm_ttft_ms": self.llm_ttft_ms,
        }
