"""
Aether Canvas - Data Models
Reactive QObject wrapper classes for nodes and relational edges.
"""

from pathlib import Path
from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal


class Node(QObject):
    positionChanged = pyqtSignal()
    focusChanged = pyqtSignal()
    filePathChanged = pyqtSignal()
    clusterIdChanged = pyqtSignal(int)

    def __init__(
        self,
        id: int,
        file_path: str,
        x: float = 0.0,
        y: float = 0.0,
        focus: float = 0.35,
        cluster_id: int = -1,
    ):
        super().__init__()
        self._id = id
        self._file_path = file_path
        self._x = x
        self._y = y
        self._vx = 0.0
        self._vy = 0.0
        self._focus = focus
        self._cluster_id = cluster_id
        self._extension = Path(file_path).suffix if file_path else ""

    # --- ID ---
    @pyqtProperty(int, constant=True)
    def id(self) -> int:
        return self._id

    # --- File Path & Name ---
    @pyqtProperty(str, notify=filePathChanged)
    def filePath(self) -> str:
        return self._file_path

    @filePath.setter
    def filePath(self, val: str):
        if self._file_path != val:
            self._file_path = val
            self._extension = Path(val).suffix if val else ""
            self.filePathChanged.emit()

    @pyqtProperty(str, notify=filePathChanged)
    def fileName(self) -> str:
        return Path(self._file_path).name if self._file_path else ""

    @pyqtProperty(str, notify=filePathChanged)
    def extension(self) -> str:
        return self._extension or (Path(self._file_path).suffix if self._file_path else "")

    # --- Positions & Velocities ---
    @pyqtProperty(float, notify=positionChanged)
    def x(self) -> float:
        return self._x

    @x.setter
    def x(self, val: float):
        if self._x != val:
            self._x = val
            self.positionChanged.emit()

    @pyqtProperty(float, notify=positionChanged)
    def y(self) -> float:
        return self._y

    @y.setter
    def y(self, val: float):
        if self._y != val:
            self._y = val
            self.positionChanged.emit()

    @property
    def vx(self) -> float:
        return self._vx

    @vx.setter
    def vx(self, val: float):
        self._vx = val

    @property
    def vy(self) -> float:
        return self._vy

    @vy.setter
    def vy(self, val: float):
        self._vy = val

    # --- Cognitive Focus Weight ---
    @pyqtProperty(float, notify=focusChanged)
    def focus(self) -> float:
        return self._focus

    @focus.setter
    def focus(self, val: float):
        if abs(self._focus - val) > 0.001:
            self._focus = val
            self.focusChanged.emit()

    # --- Cluster Membership ---
    @pyqtProperty(int, notify=clusterIdChanged)
    def clusterId(self) -> int:
        return self._cluster_id

    @clusterId.setter
    def clusterId(self, val: int):
        if self._cluster_id != val:
            self._cluster_id = val
            self.clusterIdChanged.emit(val)


class Edge(QObject):
    weightChanged = pyqtSignal()

    def __init__(
        self,
        source_id: int,
        target_id: int,
        edge_type: str = "explicit",
        weight: float = 1.0,
    ):
        super().__init__()
        self._source_id = source_id
        self._target_id = target_id
        self._edge_type = edge_type
        self._weight = weight

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
            self.weightChanged.emit()