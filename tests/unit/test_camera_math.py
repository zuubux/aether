"""
Unit tests for Canvas Camera Math & Viewport Projection.
Tests central deadzone calculations, camera target steering math, and coordinate projections.
"""

def calculate_camera_target(node_x: float, node_y: float, screen_width: float = 2560.0, screen_height: float = 1440.0) -> tuple[float, float]:
    """
    Calculates viewport camera target position (targetX, targetY) to center a target node in world coordinates.
    Matching Canvas.qml camera framing formula:
      targetX = screenWidth / 2 - node_x
      targetY = screenHeight / 2 - node_y
    """
    target_x = (screen_width / 2.0) - node_x
    target_y = (screen_height / 2.0) - node_y
    return target_x, target_y


def is_in_central_deadzone(node_x: float, node_y: float, viewport_center_x: float = 1280.0, viewport_center_y: float = 720.0, deadzone_radius: float = 400.0) -> bool:
    """Checks whether node coordinates fall within central deadzone where camera steering is suppressed."""
    dx = node_x - viewport_center_x
    dy = node_y - viewport_center_y
    dist_sq = dx * dx + dy * dy
    return dist_sq <= (deadzone_radius * deadzone_radius)


def test_camera_target_calculation():
    # Node 2 at (4060.5, 4006.9)
    # Target Screen: 2560 x 1440
    tx, ty = calculate_camera_target(4060.5, 4006.9, 2560.0, 1440.0)
    assert abs(tx - (-2780.5)) < 1.0
    assert abs(ty - (-3286.9)) < 1.0


def test_central_deadzone_math():
    # Central deadzone around (1280, 720) with radius 400
    # Node at (1280, 720) is inside
    assert is_in_central_deadzone(1280.0, 720.0) is True

    # Node at (1350, 750) is inside (dist ~ 76.1)
    assert is_in_central_deadzone(1350.0, 750.0) is True

    # Node at (3000, 3000) is far outside (dist ~ 2855)
    assert is_in_central_deadzone(3000.0, 3000.0) is False
