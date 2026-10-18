"""
Horizon Controller Implementation
Dynamic horizon header state: user persona/identity and ambient environmental status.
"""

import getpass
import logging
import platform
import resource
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

logger = logging.getLogger("aia_canvas.controllers.horizon_controller")


class HorizonController(QObject):
    """
    Domain controller managing dynamic horizon identity and ambient status.
    Provides reactive properties for Stage 0 minimal horizon anchors and
    on-demand system telemetry for the diagnostics HUD.
    """

    identityChanged = pyqtSignal(str)
    ambientStatusChanged = pyqtSignal(str)
    diagnosticsChanged = pyqtSignal()

    def __init__(
        self,
        ambient_status: Optional[str] = None,
        parent: Optional[QObject] = None,
        bridge: Optional[QObject] = None,
        **kwargs,
    ):
        if ambient_status is not None and not isinstance(ambient_status, str):
            if isinstance(ambient_status, QObject) and parent is None:
                parent = ambient_status
            ambient_status = kwargs.get("ambient_status", None)

        super().__init__(parent)
        user = getpass.getuser().upper()
        host = platform.node().split(".")[0].upper()
        self._identity: str = f"{user} · {host}"
        self._ambient_status: str = ambient_status if ambient_status is not None else "South Jordan · Fair"
        self._bridge = bridge
        self._hostname: str = host
        self._username: str = user
        self._os_kernel: str = ""
        self._memory_rss: float = 0.0
        self._weaver_status: Dict[str, Any] = {"is_connected": False, "entity_count": 0, "db_path": ""}
        self._stage_metrics: Dict[str, int] = {"active_count": 0, "capacity": 0}
        self.refresh_diagnostics()

    @pyqtProperty(str, notify=diagnosticsChanged)
    def hostname(self) -> str:
        return self._hostname

    @pyqtProperty(str, notify=diagnosticsChanged)
    def username(self) -> str:
        return self._username

    @pyqtProperty(str, notify=diagnosticsChanged)
    def osKernel(self) -> str:
        return self._os_kernel

    @pyqtProperty(float, notify=diagnosticsChanged)
    def memoryRss(self) -> float:
        """Process RSS memory in MB."""
        return self._memory_rss

    @pyqtProperty("QVariantMap", notify=diagnosticsChanged)
    def weaverStatus(self) -> Dict[str, Any]:
        """Dict with is_connected (bool), entity_count (int), db_path (str)."""
        return self._weaver_status

    @pyqtProperty("QVariantMap", notify=diagnosticsChanged)
    def stageMetrics(self) -> Dict[str, int]:
        """Dict with active_count (int) and capacity (int)."""
        return self._stage_metrics

    @staticmethod
    def _read_memory_rss_mb() -> float:
        maxrss = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        # ru_maxrss is KiB on Linux, bytes on macOS.
        return maxrss / (1024.0 * 1024.0) if sys.platform == "darwin" else maxrss / 1024.0

    @staticmethod
    def _read_weaver_status() -> Dict[str, Any]:
        db_path = Path.home() / ".config" / "aether" / "weaver_graph.db"
        status: Dict[str, Any] = {"is_connected": False, "entity_count": 0, "db_path": str(db_path)}
        if not db_path.exists():
            return status
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=0.2)
            try:
                status["entity_count"] = int(conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0])
                status["is_connected"] = True
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.debug("Weaver DB inspection failed: %s", exc)
        return status

    def _read_stage_metrics(self) -> Dict[str, int]:
        ctrl = None
        if self._bridge is not None:
            ctrl = getattr(self._bridge, "plate_controller", None) or getattr(self._bridge, "plate_ctrl", None)
        metrics = {"active_count": 0, "capacity": 0}
        if ctrl is not None:
            try:
                metrics["active_count"] = int(ctrl.plateCount)
                metrics["capacity"] = int(ctrl.capacity)
            except (AttributeError, TypeError, ValueError) as exc:
                logger.debug("Stage metrics unavailable: %s", exc)
        return metrics

    @pyqtSlot()
    def refresh_diagnostics(self) -> None:
        """Re-queries host, Weaver DB and stage telemetry; emits diagnosticsChanged."""
        self._hostname = platform.node().split(".")[0].upper()
        self._username = getpass.getuser().upper()
        self._os_kernel = f"{platform.system()} {platform.release()}"
        self._memory_rss = self._read_memory_rss_mb()
        self._weaver_status = self._read_weaver_status()
        self._stage_metrics = self._read_stage_metrics()
        self.diagnosticsChanged.emit()

    @pyqtProperty(str, notify=identityChanged)
    def identity(self) -> str:
        """Dynamic user persona and node hostname string."""
        return self._identity

    @identity.setter
    def identity(self, value: str) -> None:
        self.set_identity(value)

    @pyqtSlot(str)
    def set_identity(self, value: str) -> None:
        if self._identity != value:
            self._identity = value
            self.identityChanged.emit(self._identity)

    @pyqtSlot(str)
    def setIdentity(self, value: str) -> None:
        self.set_identity(value)

    @pyqtSlot()
    def refresh_identity(self) -> None:
        """Re-evaluates the system username and hostname."""
        user = getpass.getuser().upper()
        host = platform.node().split(".")[0].upper()
        self.set_identity(f"{user} · {host}")

    @pyqtProperty(str, notify=ambientStatusChanged)
    def ambientStatus(self) -> str:
        """Environmental ambient status string (location/weather or configurable status)."""
        return self._ambient_status

    @ambientStatus.setter
    def ambientStatus(self, value: str) -> None:
        self.set_ambient_status(value)

    @pyqtSlot(str)
    def set_ambient_status(self, value: str) -> None:
        if self._ambient_status != value:
            self._ambient_status = value
            self.ambientStatusChanged.emit(self._ambient_status)

    @pyqtSlot(str)
    def setAmbientStatus(self, value: str) -> None:
        self.set_ambient_status(value)
