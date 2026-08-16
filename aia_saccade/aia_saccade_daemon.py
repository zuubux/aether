import time
import math
import cv2
import mediapipe as mp
from gaze_engine import get_binocular_gaze, map_range
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from pynput.mouse import Controller as MouseController

mouse = MouseController()

# --- HARDWARE & DISPLAY CONFIGURATION ---
DISPLAY_WIDTH = 7680
DISPLAY_HEIGHT = 2160

# --- BEHAVIOR TUNING ---
ALPHA = 0.25
SACCADE_MIN_DELTA_PX = 400
MOUSE_COOLDOWN_SEC = 2.0
TELEPORT_COOLDOWN_SEC = 1.2
CALIBRATION_TIME_SEC = 5.0

def run_calibration_phase(cap, landmarker):
    """
    Runs a 2-phase calibration:
    1. 3-second countdown to get ready.
    2. 10-second window to sweep gaze to screen corners.
    """
    print("Starting Calibration: 3s Get Ready + 10s Calibration...")
    
    PREP_TIME = 3.0
    CALIB_TIME = 10.0
    
    start_time = time.time()
    min_x, max_x = 1.0, 0.0
    min_y, max_y = 1.0, 0.0

    while True:
        ret, frame = cap.read()
        if not ret: break

        now = time.time()
        elapsed = now - start_time
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        result = landmarker.detect_for_video(mp_image, int(now * 1000))

        # --- PHASE 1: PREPARATION COUNTDOWN (0s to 3s) ---
        if elapsed < PREP_TIME:
            time_left = PREP_TIME - elapsed
            cv2.putText(frame, f"GET READY... Starting in {time_left:.1f}s", (20, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.putText(frame, "Prepare to look at all 4 screen corners", (20, 90), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        # --- PHASE 2: RECORDING BOUNDS (3s to 13s) ---
        elif elapsed < (PREP_TIME + CALIB_TIME):
            if result.face_landmarks:
                face = result.face_landmarks[0]
                raw_x, raw_y = get_binocular_gaze(face)

                # Record absolute extremes
                min_x = min(min_x, raw_x)
                max_x = max(max_x, raw_x)
                min_y = min(min_y, raw_y)
                max_y = max(max_y, raw_y)

            time_left = (PREP_TIME + CALIB_TIME) - elapsed
            cv2.putText(frame, f"RECORDING: SWEEP EYES TO ALL 4 CORNERS!", (20, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            cv2.putText(frame, f"Time remaining: {time_left:.1f}s", (20, 90), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Exit condition when full 13 seconds completes
        else:
            break

        cv2.imshow('AIA Saccade Daemon', frame)
        
        # Allow early quit with 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Add a 5% inner buffer so you don't have to strain your eyes to trigger edge targets
    x_buf = (max_x - min_x) * 0.05
    y_buf = (max_y - min_y) * 0.05
    
    return (min_x + x_buf, max_x - x_buf, min_y + y_buf, max_y - y_buf)

def run_symbiotic_daemon():
    base_options = python.BaseOptions(model_asset_path='face_landmarker.task')
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_faces=1
    )

    with vision.FaceLandmarker.create_from_options(options) as landmarker:
        cap = cv2.VideoCapture(0)

        # --- 1. PRE-FLIGHT CALIBRATION ---
        # Blocks the script for 5 seconds to establish personal bounds
        X_MIN, X_MAX, Y_MIN, Y_MAX = run_calibration_phase(cap, landmarker)
        print(f"Locked Bounds - X: [{X_MIN:.3f}, {X_MAX:.3f}] | Y: [{Y_MIN:.3f}, {Y_MAX:.3f}]")

        # --- 2. INFINITE TELEPORT LOOP ---
        # No more `if is_calibrating:` checks required here!
        smoothed_x, smoothed_y = 0.5, 0.67
        last_gaze_px = (DISPLAY_WIDTH // 2, DISPLAY_HEIGHT // 2)
        last_mouse_pos = mouse.position
        last_human_mouse_time = 0.0
        last_teleport_time = 0.0

        print("AIA Saccade Daemon Active. Mouse takes over when moved.")

        while True:
            ret, frame = cap.read()
            if not ret: break

            now = time.time()
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            result = landmarker.detect_for_video(mp_image, int(now * 1000))

            # Detect mouse override
            current_mouse_pos = mouse.position
            if math.dist(current_mouse_pos, last_mouse_pos) > 5.0:
                last_human_mouse_time = now
            last_mouse_pos = current_mouse_pos

            # Gaze logic
            if result.face_landmarks:
                face = result.face_landmarks[0]
                raw_x, raw_y = get_binocular_gaze(face)

                smoothed_x = (ALPHA * raw_x) + ((1 - ALPHA) * smoothed_x)
                smoothed_y = (ALPHA * raw_y) + ((1 - ALPHA) * smoothed_y)

                target_px_x = int(map_range(smoothed_x, X_MIN, X_MAX, 0, DISPLAY_WIDTH))
                target_px_y = int(map_range(smoothed_y, Y_MIN, Y_MAX, 0, DISPLAY_HEIGHT))
                current_gaze_px = (target_px_x, target_px_y)

                gaze_jump_dist = math.dist(current_gaze_px, last_gaze_px)
                last_gaze_px = current_gaze_px

                human_is_active = (now - last_human_mouse_time) < MOUSE_COOLDOWN_SEC
                in_teleport_cooldown = (now - last_teleport_time) < TELEPORT_COOLDOWN_SEC

                if not human_is_active and not in_teleport_cooldown:
                    if gaze_jump_dist > SACCADE_MIN_DELTA_PX:
                        mouse.position = (target_px_x, target_px_y)
                        last_teleport_time = now
                        last_mouse_pos = (target_px_x, target_px_y)

                state_str = "SLEEP (Mouse Active)" if human_is_active else ("COOLDOWN" if in_teleport_cooldown else "READY")
                status = f"State: [{state_str}] | Target: ({target_px_x}, {target_px_y})"
                cv2.putText(frame, status, (20, 40), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            cv2.imshow('AIA Saccade Daemon', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    run_symbiotic_daemon()