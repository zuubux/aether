# Aether Architectural Hygiene Audit Report (2026-09-06)

## 1. Codebase Inventory & Hotspots
**Top 15 Files by Line Count (Python & QML):**
1. `aia_canvas/src/bridge.py` - 1,028 lines
2. `tests/qml/test_omnibar_keys.py` - 836 lines
3. `aia_canvas/src/physics/engine.py` - 825 lines
4. `aia_canvas/src/controllers/node_controller.py` - 747 lines
5. `aia_canvas/src/qml/PdfSlate.qml` - 716 lines
6. `aia_canvas/src/qml/bar/OmniBar.qml` - 703 lines
7. `aia_canvas/src/qml/PreviewSlate.qml` - 686 lines
8. `tests/unit/test_spatial_budget.py` - 665 lines
9. `aia_canvas/src/qml/ImageSlate.qml` - 595 lines
10. `aia_canvas/src/qml/focal/FocalLensFrame.qml` - 595 lines
11. `aia_canvas/src/qml/Tendril.qml` - 551 lines
12. `tests/unit/test_conversation_engine.py` - 541 lines
13. `aia_canvas/src/qml/TableSlate.qml` - 527 lines
14. `aia_canvas/src/qml/Canvas.qml` - 508 lines
15. `aia_canvas/src/models.py` - 417 lines

**Critical Hotspots Identified:**
- **`aia_canvas/src/qml/bar/OmniBar.qml`:** Exhibits highly mixed responsibilities by directly buffering streaming tokens inside a UI component (`function onTokenReceived(chunk)`). This appends raw tokens directly into a Javascript array (`resultsList`), triggering massive UI list re-renders and blocking frame timings.
- **`aia_canvas/src/bridge.py`:** At 1,028 lines, it holds excessive state-machine complexity for IPC and streaming coordination, requiring dissection to avoid bottlenecking the GUI main thread.

## 2. Dead Code, Orphaned Imports & Deprecated Stubs
- **Duplicate Logic (Prompt Assembly):** 
  There is duplicated responsibility between `PromptAssembler.assemble_system_prompt` (in `aia_canvas/src/memory/prompt_assembler.py`) and `AetherContextBuilder.build_system_instruction` (in `aia_canvas/src/omni/context.py`). The conversation `engine.py` injects context using `PromptAssembler`, which is then unnecessarily intercepted/appended by `AetherContextBuilder` in `gemini.py`. Both redundantly load `AETHER_SYSTEM_INSTRUCTION` as the core persona.
- **Deprecated Stubs:**
  `PromptAssembler` relies on hardcoded string slicing (`_truncate_to_tokens`) and duplicates omni context variables, essentially acting as an orphaned bridging stub that overlaps with the modern `AetherContextBuilder`.

## 3. Database Schema & Storage Hygiene
- **`events.db` (Event Ledger):** 
  WAL mode is properly configured (`PRAGMA journal_mode=WAL`), and indexes (`idx_events_timestamp`, `idx_events_type`) prevent unindexed full-table scans. However, the TTL cleanup function (`prune_events` in `event_ledger.py`) issues a `DELETE` query without ever invoking a subsequent `VACUUM` command. Consequently, disk space is never truly compacted, leading to inefficient file bloat.
- **`weaver_graph.db` (Graph Store):** 
  Contains standard tables (`nodes`, `edges`, `session_logs`) and extensive virtual tables for vector embeddings. The `edges` table defines `FOREIGN KEY (source_id) REFERENCES nodes(id) ON DELETE CASCADE`. However, unless `PRAGMA foreign_keys = ON` is strictly enforced on every active SQLite connection (which does not appear consistently in the Python stores), orphaned edges will accumulate silently upon node deletion.

## 4. Test Suite Alignment & Redundancy
- **Mapped Tests:** A total of 28 test files mapped across `tests/unit/`, `tests/qml/`, and `tests/integration/`.
- **Brittle & Redundant Assertions:** 
  Heavy violation of Architectural Rule 10 (Strict Anti-Test-Bloat Policy and Fast Execution). Files like `test_omnibar_keys.py` (836 lines) and `test_node_hover_pin.py` rely extensively on `QTest.qWait(50)` and real-time wall-clock loops (`time.sleep(0.01)`), rendering the suite slow and brittle.
- **Coverage Gaps:** 
  The core memory compaction paths lack robust regression coverage. For example, `tests/unit/test_event_ledger.py` only validates the `deleted_count` scalar during the prune step, completely lacking assertions that measure post-prune file size or `VACUUM` completion.

## 5. Telemetry, Monitoring & Radar Flow
- **Signal Path Trace (`engineState`):** 
  Background Thread/Worker $\to$ `ConversationController.engineStateChanged` $\to$ `Bridge.engineStateChanged` $\to$ `Canvas.qml` $\to$ `AmbientRadarHUD`.
- **Masking Issue (`DISTILLING`):**
  Inside `aia_canvas/src/qml/Canvas.qml` (~line 500), the incoming state string is aggressively intercepted and mapped to a boolean logic gate:
  ```qml
  engineState: {
      ...
      if (b.conversation && b.conversation.isThinking) return "WORKING";
      return "LATENT";
  }
  ```
  This hardcoded block swallows the `"DISTILLING"` and `"SYNTHESIZING"` string events emitting from the Python backend, forcing the Radar HUD to only ever receive "WORKING" or "LATENT".
- **Zero-Overhead Instrumentation Hooks:**
  - **Token Latency:** Do not inspect token payloads. Hook a simple `time.time()` delta right at the SSE read yield in `GeminiProvider`, appending the raw float to a fixed-size `collections.deque(maxlen=120)`. Expose the computed mean to the GUI over a 1 Hz timer tick.
  - **Memory Compaction Duration:** Wrap the DB `DELETE` and `VACUUM` logic in `EventLedger.prune_events` with `start_time = time.perf_counter()`. Emit the duration scalar as an integer event without string parsing overhead.