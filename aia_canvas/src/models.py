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
    depthZChanged = pyqtSignal()
    isDeletedChanged = pyqtSignal()

    def __init__(
        self,
        id: int,
        file_path: str,
        x: float = 0.0,
        y: float = 0.0,
        focus: float = 0.35,
        cluster_id: int = -1,
        archetype: str = "document",
        snippet: str = "",
        size_bytes: int = 0,
        thumbnail_url: str = "",
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
        self._depth_z = 0.0
        self._extension = Path(file_path).suffix if file_path else ""
        self._archetype = archetype
        self._snippet = snippet
        self._size_bytes = size_bytes
        self._thumbnail_url = thumbnail_url
        self._is_deleted = False

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

    @pyqtProperty(str, constant=True)
    def archetype(self) -> str:
        return self._archetype

    @pyqtProperty(str, constant=True)
    def snippet(self) -> str:
        return self._snippet

    @pyqtProperty(str, constant=True)
    def thumbnailUrl(self) -> str:
        return self._thumbnail_url

    @pyqtProperty(str, constant=True)
    def thumbnail(self) -> str:
        return self._thumbnail_url

    @pyqtProperty(str, constant=True)
    def preview_path(self) -> str:
        return self._thumbnail_url or self._file_path

    @pyqtProperty(str, constant=True)
    def previewUrl(self) -> str:
        return self._thumbnail_url or self._file_path

    @pyqtProperty(str, notify=filePathChanged)
    def path(self) -> str:
        return self._file_path

    @pyqtProperty(int, constant=True)
    def sizeBytes(self) -> int:
        return self._size_bytes

    def to_dict(self) -> dict:
        return {
            "id": self._id,
            "filePath": self._file_path,
            "file_path": self._file_path,
            "path": self._file_path,
            "fileName": Path(self._file_path).name if self._file_path else "",
            "extension": self.extension,
            "archetype": self._archetype,
            "snippet": self._snippet,
            "thumbnail": self._thumbnail_url,
            "thumbnailUrl": self._thumbnail_url,
            "thumbnail_url": self._thumbnail_url,
            "preview_path": self._thumbnail_url or self._file_path,
            "previewUrl": self._thumbnail_url or self._file_path,
            "sizeBytes": self._size_bytes,
            "size_bytes": self._size_bytes,
            "x": self._x,
            "y": self._y,
            "focus": self._focus,
            "clusterId": self._cluster_id,
        }

    def __getitem__(self, item: str):
        if item in ("file_path", "path"):
            return self._file_path
        if item in ("thumbnail_url", "thumbnail"):
            return self._thumbnail_url
        if item in ("preview_path", "previewUrl"):
            return self._thumbnail_url or self._file_path
        if item in ("size_bytes", "sizeBytes"):
            return self._size_bytes
        if item in ("file_name", "fileName"):
            return self.fileName
        if hasattr(self, item):
            val = getattr(self, item)
            return val
        raise KeyError(item)

    def get(self, key: str, default=None):
        try:
            return self[key]
        except KeyError:
            return default

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

    # --- Depth Z ---
    @pyqtProperty(float, notify=depthZChanged)
    def depthZ(self) -> float:
        return self._depth_z

    @depthZ.setter
    def depthZ(self, val: float):
        if abs(self._depth_z - val) > 0.001:
            self._depth_z = val
            self.depthZChanged.emit()

    @pyqtProperty(bool, notify=isDeletedChanged)
    def isDeleted(self) -> bool:
        return self._is_deleted

    @isDeleted.setter
    def isDeleted(self, val: bool):
        if self._is_deleted != val:
            self._is_deleted = val
            self.isDeletedChanged.emit()


class Edge(QObject):
    weightChanged = pyqtSignal()
    edgeChanged = pyqtSignal()

    def __init__(
        self,
        source_id: int,
        target_id: int,
        edge_type: str = "explicit",
        weight: float = 1.0,
        category: str = "topological",
    ):
        super().__init__()
        self._source_id = source_id
        self._target_id = target_id
        self._edge_type = edge_type
        self._weight = weight
        self._category = category

    @pyqtProperty(str, constant=True)
    def category(self) -> str:
        return self._category

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