# Aether Bridge Interface Audit

This document catalogs all PySide6 interfaces (`@Property`, `@Slot`, and `Signal`) currently defined in `aia_canvas/src/bridge.py` and maps them to their future domain controller destinations.

## 1. CanvasController
**Domain:** Viewport coordinates (pan, center, bounds), Aperture level and zoom state.

### Properties
* `workbenchWidth: float` (Signal: `workbenchDimensionsChanged`)
  * **QML Usage:** `Node.qml`
* `workbenchHeight: float` (Signal: `workbenchDimensionsChanged`)
  * **QML Usage:** `Node.qml`
* `wingWidth: float` (Signal: `workbenchDimensionsChanged`)
  * **QML Usage:** `Node.qml`
* `aperture: float` (Signal: `apertureChanged`)
  * **QML Usage:** `Node.qml`

### Slots
* `set_workbench_dimensions(width: float, height: float)`
  * **QML Usage:** `Node.qml`
* `update_viewport_dimensions(width: float, height: float)`
  * **QML Usage:** `Canvas.qml`
* `adjust_aperture(delta: float)`
  * **QML Usage:** `Canvas.qml` / `Node.qml`

### Signals
* `workbenchDimensionsChanged()`
* `apertureChanged(float)`

---

## 2. NodeController
**Domain:** Node selection / multi-select state, Hover dispatch and hover dwell notifications, External file manager launch & file opening slots, Node content.

### Properties
* `selectedNodeId: int` (Signal: `selectedNodeChanged`)
  * **QML Usage:** `Node.qml`
* `hoveredNodeId: int` (Signal: `hoveredNodeChanged`)
  * **QML Usage:** `Node.qml`

### Slots
* `select_node(node_id: int)`
  * **QML Usage:** `Node.qml`, `PreviewSlate.qml`, `OmniBar.qml`
* `set_hovered_node(node_id: int)`
  * **QML Usage:** `Node.qml`
* `navigate_to_link(target_name: str)`
  * **QML Usage:** `Node.qml`, `PreviewSlate.qml`
* `open_in_file_manager(file_path: str)`
  * **QML Usage:** `Node.qml`, `PreviewSlate.qml`
* `open_in_external_editor(file_path: str)`
  * **QML Usage:** `Node.qml`, `PreviewSlate.qml`
* `save_node_content(node_id: int, new_content: str)`
  * **QML Usage:** `PreviewSlate.qml`
* `is_image_file(file_path: str) -> bool`
  * **QML Usage:** `Node.qml`
* `get_image_source(file_path: str) -> str`
  * **QML Usage:** `ImageSlate.qml`
* `copy_image_to_clipboard(file_path: str) -> bool`
  * **QML Usage:** `ImageSlate.qml`
* `get_pdf_page_count(file_path: str) -> int`
  * **QML Usage:** `PdfSlate.qml`
* `get_pdf_page_image(file_path: str, page_index: int, target_width: int) -> str`
  * **QML Usage:** `PdfSlate.qml`
* `copy_pdf_page_to_clipboard(file_path: str, page_index: int) -> bool`
  * **QML Usage:** `PdfSlate.qml`
* `get_csv_preview(file_path: str, max_rows: int) -> dict`
  * **QML Usage:** `TableSlate.qml`
* `get_csv_data(file_path: str, max_rows: int) -> dict`
  * **QML Usage:** `TableSlate.qml`
* `update_csv_cell(file_path: str, row_idx: int, col_idx: int, new_value: str) -> bool`
  * **QML Usage:** `TableSlate.qml`
* `copy_csv_data(file_path: str) -> bool`
  * **QML Usage:** `TableSlate.qml`
* `pin_node(node_id: int, x: float, y: float)`
  * **QML Usage:** `Node.qml`
* `update_drag_pos(node_id: int, x: float, y: float)`
  * **QML Usage:** `Node.qml`
* `release_node(node_id: int)`
  * **QML Usage:** `Node.qml`
* `set_custom_anchor(node_id: int, x: float, y: float)`
  * **QML Usage:** `Node.qml`

### Signals
* `selectedNodeChanged(int)`
* `hoveredNodeChanged(int)`
* `nodeRemoved(int)`

---

## 3. PhysicsController
**Domain:** Tendril physics loops and force integration, Node positional spring vectors and damping, and Graph structure.

### Properties
* `nodes: List[Node]` (Signal: `nodesChanged`)
  * **QML Usage:** `Canvas.qml`
* `edges: List[Edge]` (Signal: `edgesChanged`)
  * **QML Usage:** `Tendril.qml`, `Canvas.qml`
* `clusterHalos: list` (Signal: `clusterHalosChanged`)
  * **QML Usage:** `ClusterHalo.qml`, `Node.qml`
* `physicsFrametime: float` (Signal: `telemetryChanged`)
  * **QML Usage:** `OmniBar.qml`
* `activeNodeCount: int` (Signal: `telemetryChanged`)
  * **QML Usage:** `OmniBar.qml`
* `activeEdgeCount: int` (Signal: `telemetryChanged`)
  * **QML Usage:** `OmniBar.qml`
* `isConnected: bool` (Signal: `connectionStatusChanged`)
  * **QML Usage:** `OmniBar.qml`

### Slots
* `get_downstream_count(node_id: int) -> int`
  * **QML Usage:** `Node.qml`
* `get_relation_type(node_id: int) -> str`
  * **QML Usage:** `Node.qml`

### Signals
* `nodesChanged()`
* `edgesChanged()`
* `clusterHalosChanged()`
* `telemetryChanged()`
* `connectionStatusChanged(bool)`

---

## 4. SearchController
**Domain:** Search queries and semantic match highlights, Filter criteria and search result arrays.

### Properties
(No specific Search properties, mostly handled via signals)

### Slots
* `submit_query(query: str)`
  * **QML Usage:** `OmniBar.qml`
* `clear_search()`
  * **QML Usage:** `OmniBar.qml`
* `set_staged_nodes(node_id_strs: list, viewport_w: float, shelf_y: float)`
  * **QML Usage:** `OmniBar.qml`

### Signals
* `searchResultsReceived(list)`
* `searchCleared()`
