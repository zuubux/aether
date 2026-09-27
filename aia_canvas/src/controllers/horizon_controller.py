"""
Horizon Controller Implementation
Dynamic horizon header state: user persona/identity and ambient environmental status.
"""

import getpass
import logging
import platform
from typing import Optional

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

logger = logging.getLogger("aia_canvas.controllers.horizon_controller")


class HorizonController(QObject):
    """
    Domain controller managing dynamic horizon identity and ambient status.
    Provides reactive properties for Stage 0 minimal horizon anchors.
    """

    identityChanged = pyqtSignal(str)
    ambientStatusChanged = pyqtSignal(str)

    def __init__(
        self,
        ambient_status: Optional[str] = None,
        parent: Optional[QObject] = None,
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
