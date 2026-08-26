import os
import sys
import subprocess
import urllib.parse
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QThreadPool, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QGuiApplication
from workers.media_worker import CsvWorker, ImageWorker, PdfWorker

from .base_controller import BaseController

weaver_src = str(Path(__file__).resolve().parents[3] / "aia_weaver" / "src")
if weaver_src not in sys.path and os.path.exists(weaver_src):
    sys.path.insert(0, weaver_src)


class NodeController(BaseController):
    """
    Controller managing node selection, hover state dispatch, hover dwell notifications,
    file actions, external editor launches, media & file adapters, and pinning/drag operations.
    """

    selectedNodeChanged = pyqtSignal(int)
    hoveredNodeChanged = pyqtSignal(int)
    nodeRemoved = pyqtSignal(int)
    edge_added = pyqtSignal(int, int, str, arguments=['source_id', 'target_id', 'edge_type'])

    # Async Media Signals
    pdfPageReady = pyqtSignal(str, int, str, arguments=['filePath', 'pageIndex', 'imagePath'])
    pdfCountReady = pyqtSignal(str, int, arguments=['filePath', 'pageCount'])
    csvDataReady = pyqtSignal(str, 'QVariantMap', arguments=['filePath', 'tableData'])
    imageReady = pyqtSignal(str, str, arguments=['filePath', 'sourceUrl'])
    mediaError = pyqtSignal(str, str, arguments=['filePath', 'errorMessage'])

    @pyqtProperty(int, notify=selectedNodeChanged)
    def selectedNodeId(self) -> int:
        return getattr(self.bridge, "_selected_node_id", 0)

    @pyqtProperty(int, notify=hoveredNodeChanged)
    def hoveredNodeId(self) -> int:
        return getattr(self.bridge, "_hovered_node_id", 0)

    @pyqtSlot(int)
    def select_node(self, node_id: int):
        if hasattr(self.bridge, "_wake_physics"):
            self.bridge._wake_physics()
            
        selected_id = getattr(self.bridge, "_selected_node_id", 0)
        if selected_id != node_id:
            self.bridge._selected_node_id = node_id
            
            if node_id > 0:
                if hasattr(self.bridge, "physics") and self.bridge.physics:
                    if node_id in self.bridge.physics_engine.recent_node_ids:
                        self.bridge.physics_engine.recent_node_ids.remove(node_id)
                    self.bridge.physics_engine.recent_node_ids.insert(0, node_id)
                    self.bridge.physics_engine.recent_node_ids = self.bridge.physics_engine.recent_node_ids[:8]

            if not getattr(self.bridge, "_search_active", False) and hasattr(self.bridge, "_recalculate_focal_weights"):
                self.bridge._recalculate_focal_weights(node_id)
            self.selectedNodeChanged.emit(node_id)

        if node_id == 0:
            if hasattr(self.bridge, "_focal_edges"):
                self.bridge._focal_edges = []
            if hasattr(self.bridge, "edgesChanged"):
                self.bridge.edgesChanged.emit()
            self.set_hovered_node(0)
            return

        is_connected = getattr(self.bridge, "_is_connected", False)
        if is_connected and node_id > 0:
            if hasattr(self.bridge, "ipc") and self.bridge.ipc:
                self.bridge.ipc.call_rpc_sync(
                    "touch_node",
                    {"node_id": node_id, "event_type": "focus"},
                    callback=getattr(self.bridge, "_handle_touch_node_response", None),
                )

                self.bridge.ipc.call_rpc_sync(
                    "get_neighbors",
                    {"node_id": node_id},
                    callback=getattr(self.bridge, "_handle_neighbors_response", None),
                )

    @pyqtSlot(int)
    def set_hovered_node(self, node_id: int):
        hovered_id = getattr(self.bridge, "_hovered_node_id", 0)
        if hovered_id != node_id:
            self.bridge._hovered_node_id = node_id
            self.hoveredNodeChanged.emit(node_id)
            if hasattr(self.bridge, "_wake_physics"):
                self.bridge._wake_physics()
                
            is_connected = getattr(self.bridge, "_is_connected", False)
            if is_connected and node_id > 0:
                if hasattr(self.bridge, "ipc") and self.bridge.ipc:
                    self.bridge.ipc.call_rpc_sync(
                        "get_neighbors",
                        {"node_id": node_id},
                        callback=getattr(self.bridge, "_handle_ambient_edges_response", None),
                    )

    @pyqtSlot(str)
    def navigate_to_link(self, target_name: str):
        if hasattr(self.bridge, "_wake_physics"):
            self.bridge._wake_physics()
        target_clean = target_name.lower().strip()
        if target_clean.endswith(".md") or target_clean.endswith(".txt"):
            target_clean = target_clean.rsplit(".", 1)[0]
            
        if hasattr(self.bridge, "store") and self.bridge.store:
            nodes = self.bridge.store.get_all_nodes()
            for node in nodes:
                node_file = node.fileName.lower()
                if node_file.endswith(".md") or node_file.endswith(".txt"):
                    node_file = node_file.rsplit(".", 1)[0]
                    
                if node_file == target_clean or node.fileName.lower() == target_clean:
                    self.select_node(node.id)
                    break

    @pyqtSlot(str)
    def open_in_file_manager(self, file_path: str):
        from utils.desktop import open_in_file_manager as desktop_open_file_manager
        if not desktop_open_file_manager(file_path):
            self.log_error(f"Failed to open {file_path} in file manager.")

    @pyqtSlot(str)
    def open_in_external_editor(self, file_path: str):
        from utils.desktop import open_in_external_editor as desktop_open_editor
        if not desktop_open_editor(file_path):
            self.log_error(f"Failed to open {file_path} in external editor.")

    @pyqtSlot(int, str)
    def save_node_content(self, node_id: int, new_content: str):
        is_connected = getattr(self.bridge, "_is_connected", False)
        if not is_connected or node_id <= 0:
            return
            
        def _handle_save(result: Any, error: str | None):
            if error:
                self.log_error(f"Failed to save node {node_id}: {error}")
            else:
                self.log_info(f"Node {node_id} successfully saved to disk and DB.")

        if hasattr(self.bridge, "ipc") and self.bridge.ipc:
            self.bridge.ipc.call_rpc_sync(
                "save_node_content",
                {"node_id": node_id, "content": new_content},
                callback=_handle_save
            )

    @pyqtSlot(int, int, str)
    def create_edge(self, source_id: int, target_id: int, edge_type: str = "explicit"):
        is_connected = getattr(self.bridge, "_is_connected", False)
        if not is_connected or source_id <= 0 or target_id <= 0:
            return

        def _handle_create(result: Any, error: str | None):
            if error:
                self.log_error(f"Failed to create edge: {error}")
            else:
                self.log_info(f"Edge successfully created between {source_id} and {target_id}.")

        if hasattr(self.bridge, "ipc") and self.bridge.ipc:
            self.bridge.ipc.call_rpc_sync(
                "create_edge",
                {"source_id": source_id, "target_id": target_id, "edge_type": edge_type},
                callback=_handle_create
            )
            
        # Update local physics engine & edge models immediately
        if hasattr(self.bridge, "_upsert_edge"):
            from models import Edge
            edge_obj = Edge(
                source_id=int(source_id),
                target_id=int(target_id),
                edge_type=str(edge_type),
                category="topological",
                weight=1.0,
                lane_offset=-1
            )
            self.bridge._upsert_edge(edge_obj)
            
            # Since _upsert_edge handles structural edges but we also want to ensure focal update
            if getattr(self.bridge, "_selected_node_id", 0) in (int(source_id), int(target_id)):
                self.bridge._focal_edges.append(edge_obj)
                
                # Deduplicate to fix lane offsets if temporal already exists
                if hasattr(self.bridge, "_get_deduplicated_edges"):
                    self.bridge._focal_edges = self.bridge._get_deduplicated_edges(self.bridge._focal_edges)

                if hasattr(self.bridge, "_recalculate_focal_weights"):
                    self.bridge._recalculate_focal_weights(self.bridge._selected_node_id)
        
        if hasattr(self.bridge, "edgesChanged"):
            self.bridge.edgesChanged.emit()
            if hasattr(self.bridge, "ambientEdgesChanged"):
                self.bridge.ambientEdgesChanged.emit()
            
        if hasattr(self, "edge_added"):
            self.edge_added.emit(source_id, target_id, edge_type)

    @pyqtSlot(str, result=bool)
    def is_image_file(self, file_path: str) -> bool:
        if not file_path:
            return False
        clean_path = urllib.parse.unquote(file_path.replace("file://", ""))
        ext = os.path.splitext(clean_path)[1].lstrip(".").lower()
        supported = getattr(self.bridge, "_SUPPORTED_IMAGE_EXTS", set())
        return ext in supported

    @pyqtSlot(str)
    def request_image_source(self, file_path: str):
        if not file_path:
            return
        failed_set = getattr(self.bridge, "_failed_image_conversions", set())
        worker = ImageWorker(file_path, failed_set)
        worker.signals.imageReady.connect(self.imageReady)
        worker.signals.mediaError.connect(self.mediaError)
        QThreadPool.globalInstance().start(worker)

    @pyqtSlot(str, result=bool)
    def copy_image_to_clipboard(self, file_path: str) -> bool:
        if not file_path:
            return False
        from PyQt6.QtGui import QImage
        clean_path = urllib.parse.unquote(file_path.replace("file://", ""))
        image = QImage(clean_path)
        if image.isNull():
            return False
        clipboard = QGuiApplication.clipboard()
        clipboard.setImage(image)
        return True

    @pyqtSlot(str)
    def request_pdf_page_count(self, file_path: str):
        if not file_path:
            return
        worker = PdfWorker(file_path, "count")
        worker.signals.pdfCountReady.connect(self.pdfCountReady)
        worker.signals.mediaError.connect(self.mediaError)
        QThreadPool.globalInstance().start(worker)

    @pyqtSlot(str, result=int)
    def get_pdf_page_count(self, file_path: str) -> int:
        if not file_path:
            return 0
        try:
            clean_path = urllib.parse.unquote(file_path.replace("file://", ""))
            if not os.path.exists(clean_path):
                return 0
            try:
                import pypdfium2 as pdfium
                doc = pdfium.PdfDocument(clean_path)
                return len(doc)
            except ImportError:
                try:
                    import fitz
                    doc = fitz.open(clean_path)
                    return len(doc)
                except ImportError:
                    self.log_error("Neither pypdfium2 nor pymupdf (fitz) is available for PDF rendering.")
                    return 0
        except (OSError, ImportError, FileNotFoundError) as e:
            self.log_error(f"Error getting PDF page count for {file_path}: {e}")
            return 0

    @pyqtSlot(str, int, int)
    @pyqtSlot(str, int)
    @pyqtSlot(str)
    def request_pdf_page(self, file_path: str, page_index: int = 0, target_width: int = 1800):
        if not file_path:
            return
        worker = PdfWorker(file_path, "page", page_index, target_width)
        worker.signals.pdfPageReady.connect(self.pdfPageReady)
        worker.signals.mediaError.connect(self.mediaError)
        QThreadPool.globalInstance().start(worker)

    def get_pdf_page_image(self, file_path: str, page_index: int = 0, target_width: int = 1800) -> str:
        if not file_path:
            return ""
        try:
            import hashlib
            clean_path = urllib.parse.unquote(file_path.replace("file://", ""))
            if not os.path.exists(clean_path):
                return ""
            mtime = os.path.getmtime(clean_path)
            cache_key = f"{clean_path}_{page_index}_{target_width}_{mtime}"
            h = hashlib.md5(cache_key.encode('utf-8')).hexdigest()
            
            cache_dir = os.path.expanduser("~/.cache/aether/pdf_cache")
            os.makedirs(cache_dir, exist_ok=True)
            cached_path = os.path.join(cache_dir, f"{h}.png")
            
            if os.path.exists(cached_path):
                return "file://" + cached_path
                
            try:
                import pypdfium2 as pdfium
                doc = pdfium.PdfDocument(clean_path)
                if page_index < 0 or page_index >= len(doc):
                    return ""
                page = doc[page_index]
                width, height = page.get_size()
                scale = target_width / width if width > 0 else 1.5
                bitmap = page.render(scale=scale)
                pil_img = bitmap.to_pil()
                pil_img.save(cached_path, "PNG")
                return "file://" + cached_path
            except ImportError:
                try:
                    import fitz
                    doc = fitz.open(clean_path)
                    if page_index < 0 or page_index >= len(doc):
                        return ""
                    page = doc[page_index]
                    w = page.rect.width
                    scale = target_width / w if w > 0 else 1.5
                    mat = fitz.Matrix(scale, scale)
                    pix = page.get_pixmap(matrix=mat)
                    pix.save(cached_path)
                    return "file://" + cached_path
                except Exception as e:
                    self.log_error(f"Failed rendering PDF sync: {e}")
                    return ""
        except Exception as e:
            self.log_error(f"Error in get_pdf_page_image: {e}")
            return ""

    @pyqtSlot(str, int, result=bool)
    @pyqtSlot(str, result=bool)
    def copy_pdf_page_to_clipboard(self, file_path: str, page_index: int = 0) -> bool:
        if not file_path:
            return False
        try:
            cached_img_url = self.get_pdf_page_image(file_path, page_index, target_width=2000)
            if not cached_img_url:
                return False
            clean_img_path = urllib.parse.unquote(cached_img_url.replace("file://", ""))
            if not os.path.exists(clean_img_path):
                return False
            
            from PyQt6.QtGui import QImage
            image = QImage(clean_img_path)
            if image.isNull():
                return False
            
            clipboard = QGuiApplication.clipboard()
            clipboard.setImage(image)
            return True
        except (OSError, FileNotFoundError) as e:
            self.log_error(f"Error copying PDF page to clipboard for {file_path}: {e}")
            return False

    @pyqtSlot(str, int)
    @pyqtSlot(str)
    def request_csv_data(self, file_path: str, max_rows: int = 1000):
        if not file_path:
            return
        worker = CsvWorker(file_path, max_rows)
        worker.signals.csvDataReady.connect(self.csvDataReady)
        worker.signals.mediaError.connect(self.mediaError)
        QThreadPool.globalInstance().start(worker)

    @pyqtSlot(str, int, int, str, result=bool)
    def update_csv_cell(self, file_path: str, row_idx: int, col_idx: int, new_value: str) -> bool:
        if not file_path:
            return False
        try:
            clean_path = urllib.parse.unquote(file_path.replace("file://", ""))
            if not os.path.exists(clean_path):
                return False

            import csv
            delimiter = ","
            quoting = csv.QUOTE_MINIMAL
            try:
                with open(clean_path, "r", encoding="utf-8", errors="ignore") as f:
                    sample = f.read(4096)
                    if sample:
                        sniffer = csv.Sniffer()
                        dialect = sniffer.sniff(sample, delimiters=[',', '\t', ';'])
                        delimiter = dialect.delimiter
                        quoting = dialect.quoting
            except csv.Error:
                if clean_path.endswith(".tsv"):
                    delimiter = "\t"

            rows = []
            with open(clean_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f, delimiter=delimiter)
                for r in reader:
                    rows.append(r)

            target_csv_row_idx = row_idx + 1

            if target_csv_row_idx < len(rows):
                if col_idx < len(rows[target_csv_row_idx]):
                    rows[target_csv_row_idx][col_idx] = new_value
                else:
                    while len(rows[target_csv_row_idx]) <= col_idx:
                        rows[target_csv_row_idx].append("")
                    rows[target_csv_row_idx][col_idx] = new_value
            else:
                return False

            with open(clean_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f, delimiter=delimiter, quoting=quoting)
                writer.writerows(rows)

            self.log_info(f"Successfully updated CSV cell at row {row_idx}, col {col_idx} in {clean_path}")
            return True
        except (OSError, FileNotFoundError) as e:
            self.log_error(f"Error updating CSV cell: {e}")
            return False

    @pyqtSlot(int, float, float)
    def pin_node(self, node_id: int, x: float, y: float):
        if hasattr(self.bridge, "_wake_physics"):
            self.bridge._wake_physics()
        if hasattr(self.bridge, "physics") and self.bridge.physics:
            self.bridge.physics_engine.pin_node(node_id)
        if hasattr(self.bridge, "store") and self.bridge.store:
            node = self.bridge.store.get_node(node_id)
            if node:
                node.x = x
                node.y = y

    @pyqtSlot(int, float, float)
    def update_drag_pos(self, node_id: int, x: float, y: float):
        if hasattr(self.bridge, "_wake_physics"):
            self.bridge._wake_physics()
        if hasattr(self.bridge, "store") and self.bridge.store:
            node = self.bridge.store.get_node(node_id)
            if node:
                node.x = x
                node.y = y

    @pyqtSlot(int, float, float)
    def updateNodePosition(self, node_id: int, x: float, y: float):
        self.update_drag_pos(node_id, x, y)

    @pyqtSlot(int, float, float)
    def update_node_position(self, node_id: int, x: float, y: float):
        self.update_drag_pos(node_id, x, y)

    @pyqtSlot(int)
    def release_node(self, node_id: int):
        if hasattr(self.bridge, "_wake_physics"):
            self.bridge._wake_physics()
        if hasattr(self.bridge, "physics") and self.bridge.physics:
            self.bridge.physics_engine.unpin_node()

    @pyqtSlot(int, float, float)
    def set_custom_anchor(self, node_id: int, x: float, y: float):
        if hasattr(self.bridge, "physics") and self.bridge.physics:
            self.bridge.physics_engine.set_custom_anchor(node_id, x, y)

    @pyqtSlot(str, int, result='QVariantMap')
    @pyqtSlot(str, result='QVariantMap')
    def get_csv_preview(self, file_path: str, max_rows: int = 5) -> dict:
        if not file_path:
            return {"headers": [], "rows": [], "total_rows": 0, "total_cols": 0}
        try:
            clean_path = urllib.parse.unquote(file_path.replace("file://", ""))
            if not os.path.exists(clean_path):
                return {"headers": [], "rows": [], "total_rows": 0, "total_cols": 0}

            import csv
            delimiter = ","
            try:
                with open(clean_path, "r", encoding="utf-8", errors="ignore") as f:
                    sample = f.read(4096)
                    if sample:
                        sniffer = csv.Sniffer()
                        dialect = sniffer.sniff(sample, delimiters=[',', '\t', ';'])
                        delimiter = dialect.delimiter
            except csv.Error:
                if clean_path.endswith(".tsv"):
                    delimiter = "\t"

            headers = []
            rows = []
            total_rows = 0
            
            with open(clean_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f, delimiter=delimiter)
                try:
                    first_row = next(reader)
                    if first_row is not None:
                        headers = [str(cell).strip() for cell in first_row]
                except StopIteration:
                    return {"headers": [], "rows": [], "total_rows": 0, "total_cols": 0}
                
                for row_data in reader:
                    total_rows += 1
                    if len(rows) < max_rows:
                        rows.append([str(cell).strip() for cell in row_data])
                        
            return {
                "headers": headers,
                "rows": rows,
                "total_rows": total_rows,
                "total_cols": len(headers)
            }
        except Exception as e:
            self.log_error(f"Error in get_csv_preview: {e}")
            return {"headers": [], "rows": [], "total_rows": 0, "total_cols": 0}

    @pyqtSlot(str, result=bool)
    def copy_csv_data(self, file_path: str) -> bool:
        if not file_path:
            return False
        try:
            clean_path = urllib.parse.unquote(file_path.replace("file://", ""))
            if not os.path.exists(clean_path):
                return False
            with open(clean_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(content)
            return True
        except Exception as e:
            self.log_error(f"Error in copy_csv_data: {e}")
            return False

    @pyqtSlot(str, result=str)
    def resolve_media_url(self, file_path: str) -> str:
        if not file_path:
            return ""
        clean_path = urllib.parse.unquote(file_path.replace("file://", ""))
        abs_path = os.path.abspath(clean_path)
        if os.path.exists(abs_path):
            return QUrl.fromLocalFile(abs_path).toString()
        if file_path.startswith("file://") or file_path.startswith("http://") or file_path.startswith("https://") or file_path.startswith("qrc:/"):
            return file_path
        return "file://" + abs_path

    @pyqtSlot(str, result='QVariantList')
    def get_audio_waveform(self, file_path: str) -> list:
        if not file_path:
            return [0.0] * 64
        clean_path = urllib.parse.unquote(file_path.replace("file://", ""))
        if not hasattr(self, "_waveform_cache"):
            self._waveform_cache = {}
        if clean_path in self._waveform_cache:
            return self._waveform_cache[clean_path]

        try:
            from extractors.media import extract_audio
            _, _, payload = extract_audio(clean_path)
            if payload and "waveform" in payload and payload["waveform"]:
                wf = payload["waveform"]
                self._waveform_cache[clean_path] = wf
                return wf
        except Exception as e:
            self.log_error(f"Error generating waveform for {file_path}: {e}")

        default_wf = [0.0] * 64
        self._waveform_cache[clean_path] = default_wf
        return default_wf

    @pyqtSlot(str, result='QVariantList')
    def get_waveform(self, file_path: str) -> list:
        return self.get_audio_waveform(file_path)

    @pyqtSlot(str, result=str)
    def get_video_poster(self, file_path: str) -> str:
        if not file_path:
            return ""
        clean_path = urllib.parse.unquote(file_path.replace("file://", ""))
        if not hasattr(self, "_poster_cache"):
            self._poster_cache = {}
        if clean_path in self._poster_cache:
            return self._poster_cache[clean_path]

        try:
            from extractors.media import extract_video
            _, _, poster_path = extract_video(clean_path)
            if poster_path and os.path.exists(poster_path):
                url_str = QUrl.fromLocalFile(os.path.abspath(poster_path)).toString()
                self._poster_cache[clean_path] = url_str
                return url_str
        except Exception as e:
            self.log_error(f"Error getting video poster for {file_path}: {e}")

        self._poster_cache[clean_path] = ""
        return ""

    @pyqtSlot(str, result=str)
    def get_poster(self, file_path: str) -> str:
        return self.get_video_poster(file_path)
