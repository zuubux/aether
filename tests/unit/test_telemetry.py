"""
Unit Tests for Phase 3 Telemetry Core (TelemetrySink)
"""

import time
import pytest
from core.telemetry import TelemetrySink


def test_telemetry_sink_singleton():
    sink1 = TelemetrySink()
    sink2 = TelemetrySink.instance()
    assert sink1 is sink2


def test_telemetry_sink_rolling_deques_maxlen():
    sink = TelemetrySink.instance()
    sink.reset()

def test_telemetry_sink_metrics_recording():
    sink = TelemetrySink.instance()
    sink.reset()

    sink.record_render_fps(119.5)
    sink.record_ipc_rtt(1.8)
    sink.record_db_query(3.2)
    sink.record_llm_ttft(145.0)

    assert sink.render_fps == 119.5
    assert sink.ipc_rtt_ms == 1.8
    assert sink.db_query_ms == 3.2
    assert sink.llm_ttft_ms == 145.0

    snapshot = sink.get_snapshot()
    assert snapshot["render_fps"] == 119.5
    assert snapshot["ipc_rtt_ms"] == 1.8
    assert snapshot["db_query_ms"] == 3.2
    assert snapshot["llm_ttft_ms"] == 145.0


def test_telemetry_sink_timing_helper():
    sink = TelemetrySink.instance()
    t0 = sink.time_ns()
    time.sleep(0.005)  # 5ms
    elapsed_ms = sink.calc_ns_to_ms(t0)
    assert elapsed_ms >= 4.0  # allow small timer variance
