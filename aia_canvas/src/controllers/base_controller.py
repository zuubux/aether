import logging

from PyQt6.QtCore import QObject


class BaseController(QObject):
    """Base class for all domain controllers in the Aether Canvas bridge."""
    
    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.logger = logging.getLogger(f"aia_canvas.controllers.{self.__class__.__name__}")

    def log_info(self, message: str):
        self.logger.info(message)

    def log_error(self, message: str, error: Exception = None):
        if error:
            self.logger.error(f"{message}: {error}", exc_info=True)
        else:
            self.logger.error(message)

    def log_debug(self, message: str):
        self.logger.debug(message)
