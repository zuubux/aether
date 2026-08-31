"""
Aether Canvas - Data Models
Reactive QObject wrapper classes for nodes and relational edges.
"""

import time
from pathlib import Path
import os

from PyQt6.QtCore import QObject, QPointF, pyqtProperty, pyqtSignal


class Node(QObject):
    positionChanged = pyqtSignal()
    targetPositionChanged = pyqtSignal()
    zoneChanged = pyqtSignal()
    focusChanged = pyqtSignal()
    filePathChanged = pyqtSignal()
    clusterIdChanged = pyqtSignal(int)
    depthZChanged = pyqtSignal()
    isDeletedChanged = pyqtSignal()
    archetypeChanged = pyqtSignal()
    snippetChanged = pyqtSignal()
    thumbnailUrlChanged = pyqtSignal()

    isUserPlacedChanged = pyqtSignal()
    lastInteractionEpochChanged = pyqtSignal()
    isPinnedChanged = pyqtSignal()

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
        zone: str = "ZONE_HORIZON",
        target_x: float | None = None,
        target_y: float | None = None,
        is_user_placed: bool = False,
        last_interaction_epoch: float | None = None,
        is_pinned: bool = False,
    ):
        super().__init__()
        self._id = id
        self._file_path = file_path
        self._x = x
        self._y = y
        self._target_x = target_x if target_x is not None else x
        self._target_y = target_y if target_y is not None else y
        self._zone = zone
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
        self._is_user_placed = is_user_placed
        self._last_interaction_epoch = float(last_interaction_epoch) if last_interaction_epoch is not None else time.time()
        self._is_pinned = bool(is_pinned)

    # --- ID ---
    @pyqtProperty(int, constant=True)
    def id(self) -> int:
        return self._id

    @pyqtProperty(int, constant=True)
    def nodeId(self) -> int:
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
    def display_title(self) -> str:
        name = self.fileName
        if not name:
            return ""
        # Preserve single-dot dotfiles like .gitignore, .bashrc
        if name.startswith(".") and name.count(".") == 1:
            return name

        # Strip common compound archive suffixes
        compound_suffixes = ('.tar.gz', '.tar.bz2', '.tar.xz', '.tar.zst')
        for suffix in compound_suffixes:
            if name.lower().endswith(suffix):
                return name[:-len(suffix)]

        from pathlib import Path
        return Path(name).stem

    @pyqtProperty(str, notify=filePathChanged)
    def displayTitle(self) -> str:
        return self.display_title

    @pyqtProperty(str, notify=filePathChanged)
    def extension(self) -> str:
        return self._extension or (Path(self._file_path).suffix if self._file_path else "")

    @pyqtProperty(str, notify=archetypeChanged)
    def archetype(self) -> str:
        return self._archetype

    @pyqtProperty(str, notify=snippetChanged)
    def snippet(self) -> str:
        return self._snippet

    @property
    def _is_image(self) -> bool:
        ext = (self._extension or (Path(self._file_path).suffix if self._file_path else "")).lower()
        arch = (self._archetype or "").upper()
        return arch in ("IMAGE", "MEDIA", "ASSET") or ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico")

    @pyqtProperty(str, notify=thumbnailUrlChanged)
    def thumbnailUrl(self) -> str:
        if self._thumbnail_url and os.path.exists(self._thumbnail_url):
            return self._thumbnail_url
        return ""

    @pyqtProperty(str, notify=thumbnailUrlChanged)
    def preview_path(self) -> str:
        thumb = self.thumbnailUrl
        return thumb or (self._file_path if self._is_image else "")

    def to_dict(self) -> dict:
        thumb = self.thumbnailUrl
        prev = self.preview_path
        title = self.display_title
        return {
            "id": self._id,
            "filePath": self._file_path,
            "file_path": self._file_path,
            "path": self._file_path,
            "fileName": Path(self._file_path).name if self._file_path else "",
            "displayTitle": title,
            "display_title": title,
            "extension": self.extension,
            "archetype": self._archetype,
            "snippet": self._snippet,
            "thumbnail": thumb,
            "thumbnailUrl": thumb,
            "thumbnail_url": thumb,
            "preview_path": prev,
            "previewUrl": prev,
            "sizeBytes": self._size_bytes,
            "size_bytes": self._size_bytes,
            "x": self._x,
            "y": self._y,
            "focus": self._focus,
            "clusterId": self._cluster_id,
            "is_user_placed": self._is_user_placed,
            "isUserPlaced": self._is_user_placed,
            "last_interaction_epoch": getattr(self, "_last_interaction_epoch", 0.0),
            "lastInteractionEpoch": getattr(self, "_last_interaction_epoch", 0.0),
            "is_pinned": getattr(self, "_is_pinned", False),
            "isPinned": getattr(self, "_is_pinned", False),
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
        if item in ("display_title", "displayTitle"):
            return self.display_title
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

    # --- Zone & Target Position ---
    @pyqtProperty(str, notify=zoneChanged)
    def zone(self) -> str:
        return self._zone

    @zone.setter
    def zone(self, val: str):
        if self._zone != val:
            self._zone = val
            self.zoneChanged.emit()

    @pyqtProperty(QPointF, notify=targetPositionChanged)
    def targetPosition(self) -> QPointF:
        return QPointF(self._target_x, self._target_y)

    @targetPosition.setter
    def targetPosition(self, val: object):
        tx, ty = self._target_x, self._target_y
        if isinstance(val, QPointF):
            tx, ty = val.x(), val.y()
        elif isinstance(val, (tuple, list)) and len(val) >= 2:
            tx, ty = float(val[0]), float(val[1])
        elif isinstance(val, dict):
            tx, ty = float(val.get("x", tx)), float(val.get("y", ty))

        if abs(self._target_x - tx) > 0.001 or abs(self._target_y - ty) > 0.001:
            self._target_x = tx
            self._target_y = ty
            self.targetPositionChanged.emit()

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

    @pyqtProperty(bool, notify=isUserPlacedChanged)
    def is_user_placed(self) -> bool:
        return getattr(self, "_is_user_placed", False)

    @is_user_placed.setter
    def is_user_placed(self, val: bool):
        bval = bool(val)
        if getattr(self, "_is_user_placed", False) != bval:
            self._is_user_placed = bval
            self.isUserPlacedChanged.emit()

    @pyqtProperty(bool, notify=isUserPlacedChanged)
    def isUserPlaced(self) -> bool:
        return self.is_user_placed

    @isUserPlaced.setter
    def isUserPlaced(self, val: bool):
        self.is_user_placed = val

    # --- Temporal Decay & Pinning ---
    @pyqtProperty(float, notify=lastInteractionEpochChanged)
    def last_interaction_epoch(self) -> float:
        return getattr(self, "_last_interaction_epoch", 0.0)

    @last_interaction_epoch.setter
    def last_interaction_epoch(self, val: float):
        fval = float(val)
        if abs(getattr(self, "_last_interaction_epoch", 0.0) - fval) > 1e-4:
            self._last_interaction_epoch = fval
            self.lastInteractionEpochChanged.emit()

    @pyqtProperty(float, notify=lastInteractionEpochChanged)
    def lastInteractionEpoch(self) -> float:
        return self.last_interaction_epoch

    @lastInteractionEpoch.setter
    def lastInteractionEpoch(self, val: float):
        self.last_interaction_epoch = val

    @pyqtProperty(bool, notify=isPinnedChanged)
    def is_pinned(self) -> bool:
        return getattr(self, "_is_pinned", False)

    @is_pinned.setter
    def is_pinned(self, val: bool):
        bval = bool(val)
        if getattr(self, "_is_pinned", False) != bval:
            self._is_pinned = bval
            self.isPinnedChanged.emit()

    @pyqtProperty(bool, notify=isPinnedChanged)
    def isPinned(self) -> bool:
        return self.is_pinned

    @isPinned.setter
    def isPinned(self, val: bool):
        self.is_pinned = val


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