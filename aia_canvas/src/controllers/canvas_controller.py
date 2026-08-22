from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from .base_controller import BaseController


class CanvasController(BaseController):
    """
    Controller managing viewport coordinates, workbench dimensions, 
    wing width, and viewport aperture/zoom state.
    """
    
    workbenchDimensionsChanged = pyqtSignal()
    apertureChanged = pyqtSignal(float)

    def __init__(self, bridge, parent=None):
        super().__init__(bridge, parent)
        self._aperture: float = 1.0
        self._workbench_width: float = 1600.0
        self._workbench_height: float = 1000.0

    @pyqtProperty(float, notify=workbenchDimensionsChanged)
    def workbenchWidth(self) -> float:
        return self._workbench_width

    @pyqtProperty(float, notify=workbenchDimensionsChanged)
    def workbenchHeight(self) -> float:
        return self._workbench_height

    @pyqtProperty(float, notify=workbenchDimensionsChanged)
    def wingWidth(self) -> float:
        if hasattr(self.bridge, 'physics') and self.bridge.physics:
            return (self.bridge.physics.viewport_w - self._workbench_width) / 2.0
        return 0.0

    @pyqtProperty(float, notify=apertureChanged)
    def aperture(self) -> float:
        return self._aperture

    @pyqtSlot(float, float)
    def set_workbench_dimensions(self, width: float, height: float):
        if hasattr(self.bridge, '_wake_physics'):
            self.bridge._wake_physics()
            
        clamped_w = max(480.0, min(2600.0, width))
        clamped_h = max(320.0, min(1600.0, height))

        if abs(self._workbench_width - clamped_w) > 1.0 or abs(self._workbench_height - clamped_h) > 1.0:
            self._workbench_width = clamped_w
            self._workbench_height = clamped_h
            if hasattr(self.bridge, 'physics') and self.bridge.physics:
                self.bridge.physics.set_focal_card_dimensions(clamped_w, clamped_h)
            self.workbenchDimensionsChanged.emit()

    @pyqtSlot(float, float)
    def update_viewport_dimensions(self, width: float, height: float):
        if hasattr(self.bridge, '_wake_physics'):
            self.bridge._wake_physics()
        if hasattr(self.bridge, 'physics') and self.bridge.physics:
            self.bridge.physics.set_viewport_dimensions(width, height)
        self.workbenchDimensionsChanged.emit()

    @pyqtSlot(float)
    def adjust_aperture(self, delta: float):
        new_val = max(0.20, min(2.20, self._aperture + delta))
        if abs(new_val - self._aperture) > 0.005:
            self._aperture = new_val
            if hasattr(self.bridge, 'physics') and self.bridge.physics:
                self.bridge.physics.set_aperture(new_val)
            self.apertureChanged.emit(new_val)
            if hasattr(self.bridge, '_wake_physics'):
                self.bridge._wake_physics()
