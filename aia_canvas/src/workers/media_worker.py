import hashlib
import os
import urllib.parse
from pathlib import Path

from PyQt6.QtCore import QObject, QRunnable, QUrl, pyqtSignal


class WorkerSignals(QObject):
    pdfPageReady = pyqtSignal(str, int, str)
    pdfCountReady = pyqtSignal(str, int)
    csvDataReady = pyqtSignal(str, 'QVariantMap')
    imageReady = pyqtSignal(str, str)
    mediaError = pyqtSignal(str, str)


class PdfWorker(QRunnable):
    def __init__(self, file_path: str, action: str, page_index: int = 0, target_width: int = 1800):
        super().__init__()
        self.file_path = file_path
        self.action = action
        self.page_index = page_index
        self.target_width = target_width
        self.signals = WorkerSignals()

    def run(self):
        try:
            clean_path = urllib.parse.unquote(self.file_path.replace("file://", ""))
            if not os.path.exists(clean_path):
                self.signals.mediaError.emit(self.file_path, "File does not exist")
                return

            if self.action == "count":
                try:
                    import pypdfium2 as pdfium
                    doc = pdfium.PdfDocument(clean_path)
                    count = len(doc)
                    self.signals.pdfCountReady.emit(self.file_path, count)
                except ImportError:
                    try:
                        import fitz
                        doc = fitz.open(clean_path)
                        count = len(doc)
                        self.signals.pdfCountReady.emit(self.file_path, count)
                    except Exception as e:
                        self.signals.mediaError.emit(self.file_path, str(e))
                return

            if self.action == "page":
                mtime = os.path.getmtime(clean_path)
                cache_key = f"{clean_path}_{self.page_index}_{self.target_width}_{mtime}"
                h = hashlib.md5(cache_key.encode('utf-8')).hexdigest()
                
                cache_dir = os.path.expanduser("~/.cache/aether/pdf_cache")
                os.makedirs(cache_dir, exist_ok=True)
                cached_path = os.path.join(cache_dir, f"{h}.png")
                
                if os.path.exists(cached_path):
                    self.signals.pdfPageReady.emit(self.file_path, self.page_index, "file://" + cached_path)
                    return
                
                try:
                    import pypdfium2 as pdfium
                    doc = pdfium.PdfDocument(clean_path)
                    if self.page_index < 0 or self.page_index >= len(doc):
                        self.signals.mediaError.emit(self.file_path, "Invalid page index")
                        return
                    page = doc[self.page_index]
                    width, height = page.get_size()
                    scale = self.target_width / width if width > 0 else 1.5
                    bitmap = page.render(scale=scale)
                    pil_img = bitmap.to_pil()
                    pil_img.save(cached_path, "PNG")
                    self.signals.pdfPageReady.emit(self.file_path, self.page_index, "file://" + cached_path)
                    return
                except ImportError:
                    try:
                        import fitz
                        doc = fitz.open(clean_path)
                        if self.page_index < 0 or self.page_index >= len(doc):
                            self.signals.mediaError.emit(self.file_path, "Invalid page index")
                            return
                        page = doc[self.page_index]
                        w = page.rect.width
                        scale = self.target_width / w if w > 0 else 1.5
                        mat = fitz.Matrix(scale, scale)
                        pix = page.get_pixmap(matrix=mat)
                        pix.save(cached_path)
                        self.signals.pdfPageReady.emit(self.file_path, self.page_index, "file://" + cached_path)
                        return
                    except Exception as e:
                        self.signals.mediaError.emit(self.file_path, str(e))
        except Exception as e:
            self.signals.mediaError.emit(self.file_path, str(e))


class CsvWorker(QRunnable):
    def __init__(self, file_path: str, max_rows: int = 1000):
        super().__init__()
        self.file_path = file_path
        self.max_rows = max_rows
        self.signals = WorkerSignals()

    def run(self):
        try:
            clean_path = urllib.parse.unquote(self.file_path.replace("file://", ""))
            if not os.path.exists(clean_path):
                self.signals.mediaError.emit(self.file_path, "File does not exist")
                return
            
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
            total_cols = 0
            
            with open(clean_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f, delimiter=delimiter)
                try:
                    first_row = next(reader)
                    if first_row is not None:
                        headers = [str(cell).strip() for cell in first_row]
                        total_cols = len(headers)
                except StopIteration:
                    self.signals.csvDataReady.emit(self.file_path, {"headers": [], "rows": [], "total_rows": 0, "total_cols": 0})
                    return
                
                count = 0
                for row_data in reader:
                    count += 1
                    if self.max_rows < 0 or len(rows) < self.max_rows:
                        rows.append([str(cell).strip() for cell in row_data])
                
                total_rows = count
                
            data = {
                "headers": headers,
                "rows": rows,
                "total_rows": total_rows,
                "total_cols": total_cols
            }
            self.signals.csvDataReady.emit(self.file_path, data)
        except Exception as e:
            self.signals.mediaError.emit(self.file_path, str(e))


class ImageWorker(QRunnable):
    def __init__(self, file_path: str, failed_set: set):
        super().__init__()
        self.file_path = file_path
        self.failed_set = failed_set
        self.signals = WorkerSignals()

    def run(self):
        try:
            if self.file_path in self.failed_set:
                self.signals.mediaError.emit(self.file_path, "Previous conversion failed")
                return
            
            clean_path = urllib.parse.unquote(self.file_path.replace("file://", ""))
            if not os.path.exists(clean_path):
                p_obj = Path(clean_path)
                assets_path = p_obj.parent / "assets" / p_obj.name
                if assets_path.exists():
                    clean_path = str(assets_path)
                else:
                    path_obj = Path(clean_path).resolve()
                    if path_obj.exists():
                        clean_path = str(path_obj)
                    else:
                        self.signals.imageReady.emit(self.file_path, self.file_path)
                        return
                
            ext = os.path.splitext(clean_path)[1].lstrip(".").lower()
            if ext in ["ico", "icon"]:
                try:
                    from PIL import Image as PILImage
                    cache_dir = os.path.expanduser("~/.cache/aether")
                    os.makedirs(cache_dir, exist_ok=True)
                    
                    mtime = os.path.getmtime(clean_path)
                    cache_key = f"{clean_path}_{mtime}"
                    h = hashlib.md5(cache_key.encode('utf-8')).hexdigest()
                    cached_png = os.path.join(cache_dir, f"{h}.png")
                    
                    if not os.path.exists(cached_png):
                        with PILImage.open(clean_path) as img:
                            img.save(cached_png, "PNG")
                    
                    self.signals.imageReady.emit(self.file_path, QUrl.fromLocalFile(cached_png).toString())
                except Exception as e:
                    self.signals.mediaError.emit(self.file_path, f"Conversion error: {e}")
            else:
                self.signals.imageReady.emit(self.file_path, QUrl.fromLocalFile(clean_path).toString())
        except Exception as e:
            self.signals.mediaError.emit(self.file_path, str(e))
