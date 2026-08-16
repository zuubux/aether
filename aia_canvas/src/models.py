"""
Aether Canvas - Data Models
Reactive QObject classes matching the aia_weaver IPC schema.
"""

from pathlib import Path
from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal

class Node(QObject):
    xChanged = pyqtSignal(float)
    yChanged = pyqtSignal(float)
    focusChanged = pyqtSignal(float)
    filePathChanged = pyqtSignal(str)

    def __init__(self, id: int, file_path: str, x: float = 0.0, y: float = 0.0, focus: float = 0.35, parent=None):
        super().__init__(parent)
        self._id = id
        self._file_path = file_path
        self._extension = Path(file_path).suffix
        self._x = float(x)
        self._y = float(y)
        self.vx = 0.0  # Physics properties don't need QML bindings
        self.vy = 0.0
        self._focus = float(focus)

    @pyqtProperty(int, constant=True)
    def id(self) -> int:
        return self._id

    @pyqtProperty(str, notify=filePathChanged)
    def title(self) -> str:
        return Path(self._file_path).name if self._file_path else f"Node {self._id}"

    @pyqtProperty(str, notify=filePathChanged)
    def filePath(self) -> str:
        return self._file_path

    @filePath.setter
    def filePath(self, path: str):
        if self._file_path != path:
            self._file_path = path
            self._extension = Path(path).suffix
            self.filePathChanged.emit(path)

    @pyqtProperty(str, constant=True)
    def extension(self) -> str:
        return self._extension or Path(self._file_path).suffix

    @pyqtProperty(float, notify=xChanged)
    def x(self) -> float:
        return self._x

    @x.setter
    def x(self, val: float):
        if abs(self._x - val) > 0.001:
            self._x = val
            self.xChanged.emit(val)

    @pyqtProperty(float, notify=yChanged)
    def y(self) -> float:
        return self._y

    @y.setter
    def y(self, val: float):
        if abs(self._y - val) > 0.001:
            self._y = val
            self.yChanged.emit(val)

    @pyqtProperty(float, notify=focusChanged)
    def focus(self) -> float:
        return self._focus

    @focus.setter
    def focus(self, val: float):
        if abs(self._focus - val) > 0.001:
            self._focus = val
            self.focusChanged.emit(val)


class Edge(QObject):
    weightChanged = pyqtSignal(float)

    def __init__(self, source_id: int, target_id: int, edge_type: str, weight: float = 1.0, parent=None):
        super().__init__(parent)
        self._source_id = source_id
        self._target_id = target_id
        self._edge_type = edge_type
        self._weight = float(weight)

    @pyqtProperty(int, constant=True)
    def sourceId(self) -> int:
        return self._source_id

    @pyqtProperty(int, constant=True)
    def targetId(self) -> int:
        return self._target_id

    @pyqtProperty(str, constant=True)
    def edgeType(self) -> str:
        return self._edge_type

    @pyqtProperty(float, notify=weightChanged)
    def weight(self) -> float:
        return self._weight

    @weight.setter
    def weight(self, val: float):
        if abs(self._weight - val) > 0.001:
            self._weight = val
            self.weightChanged.emit(val)