# gaze_engine.py
"""
Aether Interface Architecture - Gaze Sensor Fusion Engine
Handles landmark extraction, single-eye geometry, and binocular failover.
"""

# MediaPipe Landmark Index Map
LEFT_EYE = {"iris": 473, "inner": 362, "outer": 263, "top": 386, "bot": 374}
RIGHT_EYE = {"iris": 468, "inner": 133, "outer": 33, "top": 159, "bot": 145}


def _calculate_single_eye(face_landmarks, eye_map):
    """Calculates relative gaze ratio for a single eye socket."""
    iris = face_landmarks[eye_map["iris"]]
    inner = face_landmarks[eye_map["inner"]]
    outer = face_landmarks[eye_map["outer"]]
    top = face_landmarks[eye_map["top"]]
    bot = face_landmarks[eye_map["bot"]]

    w = outer.x - inner.x
    h = bot.y - top.y

    if w <= 0 or h <= 0:
        return None

    x_ratio = (iris.x - inner.x) / w
    y_ratio = 1.0 - ((iris.y - top.y) / h)  # High-angle camera inversion

    return x_ratio, y_ratio


def get_binocular_gaze(face_landmarks):
    """
    Computes binocular average gaze ratio with graceful single-eye failover.
    Returns: (raw_x, raw_y)
    """
    left = _calculate_single_eye(face_landmarks, LEFT_EYE)
    right = _calculate_single_eye(face_landmarks, RIGHT_EYE)

    if left and right:
        return (left[0] + right[0]) / 2.0, (left[1] + right[1]) / 2.0
    if left:
        return left
    if right:
        return right

    return 0.5, 0.5  # Neutral fallback if both eyes occluded

def map_range(val, in_min, in_max, out_min, out_max):
    clamped_val = max(in_min, min(val, in_max))
    normalized = (clamped_val - in_min) / (in_max - in_min)
    return out_min + (normalized * (out_max - out_min))