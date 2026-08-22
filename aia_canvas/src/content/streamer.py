import mmap
import os
import logging
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, pyqtProperty, QThread

logger = logging.getLogger("aia_canvas.content_streamer")

class BufferReadWorker(QThread):
    finished_read = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, path: str, max_bytes: int = -1):
        super().__init__()
        self.path = path
        self.max_bytes = max_bytes
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            if not os.path.exists(self.path):
                self.error_occurred.emit(f"Error: File not found {self.path}")
                return

            with open(self.path, 'r', encoding='utf-8') as f:
                st = os.fstat(f.fileno())
                if st.st_size == 0:
                    self.finished_read.emit("")
                    return

                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    if self._is_cancelled:
                        return
                        
                    if self.max_bytes > 0:
                        content = mm[:self.max_bytes].decode('utf-8', errors='replace')
                    else:
                        content = mm[:].decode('utf-8', errors='replace')
                        
                    if not self._is_cancelled:
                        self.finished_read.emit(content)
                        
        except Exception as e:
            if not self._is_cancelled:
                self.error_occurred.emit(f"Error reading file: {str(e)}")


class ContentStreamer(QObject):
    """Base interface for all content streamers."""
    bufferUpdated = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._content = ""
        self._is_loading = False
        self._file_path = ""

    @pyqtProperty(str, notify=bufferUpdated)
    def content(self) -> str:
        return self._content

    @pyqtProperty(bool, notify=bufferUpdated)
    def isLoading(self) -> bool:
        return self._is_loading
        
    @pyqtProperty(str, notify=bufferUpdated)
    def filePath(self) -> str:
        return self._file_path


class MmapTextStreamer(ContentStreamer):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[BufferReadWorker] = None
        
    @pyqtSlot(str, int)
    def load_file(self, path: str, max_bytes: int = -1):
        if self._file_path == path and not self._is_loading:
            return
            
        self._file_path = path
        self._is_loading = True
        self.bufferUpdated.emit()
        
        if self._worker is not None:
            self._worker.cancel()
            self._worker.quit()
            self._worker.wait()
            self._worker = None
            
        if not path:
            self._content = ""
            self._is_loading = False
            self.bufferUpdated.emit()
            return

        self._worker = BufferReadWorker(path, max_bytes)
        self._worker.finished_read.connect(self._on_read_finished)
        self._worker.error_occurred.connect(self._on_read_error)
        self._worker.start()

    @pyqtSlot()
    def clear(self):
        self._file_path = ""
        self._content = ""
        self._is_loading = False
        if self._worker is not None:
            self._worker.cancel()
            self._worker.quit()
            self._worker.wait()
            self._worker = None
        self.bufferUpdated.emit()

    def _on_read_finished(self, content: str):
        self._content = content
        self._is_loading = False
        self.bufferUpdated.emit()

    def _on_read_error(self, error_msg: str):
        self._content = error_msg
        self._is_loading = False
        self.bufferUpdated.emit()

    def __del__(self):
        try:
            worker = getattr(self, '_worker', None)
            if worker is not None:
                worker.cancel()
                worker.quit()
                worker.wait()
        except Exception:
            pass
