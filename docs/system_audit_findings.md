# Aether System Audit Findings

## 1. Executive Summary & Health Score
**Overall Health Score: B-**
The Aether workspace demonstrates a solid architectural foundation with strict adherence to QML/Python boundaries and secure IPC designs. However, several critical areas require remediation to meet production-grade standards. Specifically, the canvas controllers exhibit synchronous I/O operations that threaten UI thread stability, and error handling across both `aia_canvas` and `aia_weaver` relies heavily on generic exception catching, which can mask critical failures. Security hygiene is generally good, but validation boundaries can be tightened.

## 2. Critical & Security Findings
**Risk Level: Medium**
*   **Path Validation in Subprocesses:**
    *   **Location:** `aia_canvas/src/controllers/node_controller.py` (Lines 109, 124)
    *   **Finding:** `open_in_file_manager` and `open_in_external_editor` use `subprocess.Popen(["xdg-open", ...])`. While `shell=True` is correctly avoided, the `file_path` argument relies on prior canonicalization. It is recommended to explicitly assert the file exists and is within allowed directories immediately before execution.
*   **IPC Payload Validation:**
    *   **Location:** `aia_canvas/src/ipc/client.py` and `aia_weaver/src/ipc/server.py`
    *   **Finding:** Message parsing relies on generic `except Exception:` blocks when handling incoming JSON. Malformed payloads can cause silent failures rather than explicit validation errors or graceful socket resets.

## 3. Performance & Threading Bottlenecks
**Risk Level: High (UI Stuttering / Frame Drops)**
*   **Synchronous File I/O in UI Thread (Node Controller):**
    *   **Location:** `aia_canvas/src/controllers/node_controller.py`
    *   **Finding:** Several slots and methods invoked directly by QML perform synchronous, blocking disk operations. This will cause UI stuttering and frame drops below the target 120 FPS.
        *   `get_image_source()`: Synchronous `PILImage.open()` (Line 195).
        *   `get_pdf_page_image()` & `get_pdf_page_count()`: Synchronous `fitz.open()` (Lines 235, 282).
        *   `_parse_csv_tsv_file()` & `copy_csv_data()`: Synchronous `f.read()` (Lines 337, 413, 460).
        *   `save_node_content()`: Synchronous file writing.
    *   **Recommendation:** Offload all disk I/O to QThreadPool, `asyncio`, or dedicated worker threads, emitting signals to update the UI upon completion.

## 4. Code Hygiene & Stale Artifact Catalog
*   **Leftover Test Harnesses / Prints:**
    *   **Location:** `aia_canvas/src/aia_context/ledger.py` (Line 191+)
    *   **Finding:** Contains leftover test harness prints (`print("Initializing ContextLedger in temp directory...")`, `print("Recording dummy event...")`). These pollute stdout and should be removed or moved to formal unit tests.
*   **Generic Exception Handling:**
    *   **Location:** Widespread (`aia_canvas/src/controllers/node_controller.py`, `aia_weaver/src/storage/db.py`, `aia_canvas/src/ipc/client.py`, etc.)
    *   **Finding:** Extensive use of `except Exception as e:` and bare `except Exception:`.
    *   **Recommendation:** Replace generic handlers with specific exceptions (e.g., `FileNotFoundError`, `json.JSONDecodeError`, `sqlite3.DatabaseError`) to prevent masking unexpected bugs.

## 5. Recommended Step-by-Step Remediation Plan
1.  **Phase 1: Threading Refactor (High Priority)**
    *   Refactor `node_controller.py` to use asynchronous tasks or background threads for all file reading/writing (PDF, Image, CSV processing).
    *   Implement signal/slot mechanisms to stream results back to the QML frontend without blocking the main event loop.
2.  **Phase 2: Error Handling Overhaul**
    *   Audit all `except Exception:` blocks across the codebase.
    *   Replace them with targeted exception types.
    *   Ensure any swallowed errors at least log explicitly using the structured `log_error` mechanism.
3.  **Phase 3: Code Cleanup**
    *   Remove the dummy testing script at the bottom of `aia_canvas/src/aia_context/ledger.py`.
    *   Audit unused imports across modules and prune them using an automated tool like `ruff` or `flake8`.
4.  **Phase 4: IPC Hardening**
    *   Introduce schema validation (e.g., `pydantic`) for IPC messages in `aia_weaver` and `aia_canvas` before processing.