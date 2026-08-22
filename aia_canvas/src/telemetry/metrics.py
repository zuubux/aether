import collections
import time

class TelemetryCollector:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TelemetryCollector, cls).__new__(cls)
            cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        self.bootstrap_completed = False
        self.bootstrap_metrics = {
            "time_to_first_frame_ms": 0.0,
            "initial_sync_duration_ms": 0.0,
            "initial_sync_message_count": 0
        }
        self._sync_start_time = time.perf_counter()
        
        # Fixed-size rolling windows for metrics
        self.frame_times = collections.deque(maxlen=120)
        self.ipc_latencies = collections.deque(maxlen=120)
        self.threadpool_active = collections.deque(maxlen=120)

    def record_frame(self, delta_ms: float):
        if not self.bootstrap_completed:
            self.bootstrap_completed = True
            self.bootstrap_metrics["time_to_first_frame_ms"] = float(delta_ms)
        else:
            self.frame_times.append(float(delta_ms))

    def record_ipc(self, latency_ms: float):
        if not self.bootstrap_completed:
            self.bootstrap_metrics["initial_sync_message_count"] += 1
            self.bootstrap_metrics["initial_sync_duration_ms"] = (time.perf_counter() - self._sync_start_time) * 1000.0
        else:
            self.ipc_latencies.append(float(latency_ms))

    def record_threadpool(self, active_threads: int):
        self.threadpool_active.append(int(active_threads))

    def get_snapshot(self) -> dict:
        def calc_stats(dq):
            if not dq:
                return {"avg": 0.0, "p50": 0.0, "p99": 0.0, "count": 0, "latest": 0.0}
            data = sorted(dq)
            n = len(data)
            return {
                "avg": sum(data) / n,
                "p50": data[n // 2] if n > 0 else 0.0,
                "p99": data[int(n * 0.99)] if n > 0 else 0.0,
                "count": n,
                "latest": dq[-1] if n > 0 else 0.0
            }

        return {
            "bootstrap": self.bootstrap_metrics,
            "steady_state": {
                "frame_times": calc_stats(self.frame_times),
                "ipc_latencies": calc_stats(self.ipc_latencies),
                "threadpool_active": calc_stats(self.threadpool_active)
            }
        }
