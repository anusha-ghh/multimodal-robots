import cv2
import mediapipe as mp
import numpy as np

BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

back_sub = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=False)

class HandTrackingState:
    latest_result = None

options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path='hand_landmarker.task'),
    running_mode=VisionRunningMode.LIVE_STREAM,
    result_callback=lambda result, output_image, timestamp_ms: setattr(HandTrackingState, 'latest_result', result)
)

cap = cv2.VideoCapture(0)
timestamp = 0

print("Press 'q' to quit.")

with HandLandmarker.create_from_options(options) as landmarker:
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            continue

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        # isolate moving obj
        fg_mask = back_sub.apply(frame)
        _, fg_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)

        # hand tracking
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        landmarker.detect_async(mp_image, timestamp)
        timestamp += 1

        if HandTrackingState.latest_result and HandTrackingState.latest_result.hand_landmarks:
            for hand_landmarks in HandTrackingState.latest_result.hand_landmarks:

                # index finger direction calculation (PIP --> TIP)
                index_tip = hand_landmarks[8]
                fx, fy = int(index_tip.x * w), int(index_tip.y * h)

                index_pip = hand_landmarks[6]

                dx = index_tip.x - index_pip.x
                dy = index_tip.y - index_pip.y

                magnitude = np.sqrt(dx**2 + dy**2)

                if magnitude > 0:
                    dx /= magnitude
                    dy /= magnitude

                # go to edge of screen because where else
                max_distance = 1000

                target_x = int(fx + dx * max_distance)
                target_y = int(fy + dy * max_distance)

                target_x = max(0, min(w - 1, target_x))
                target_y = max(0, min(h - 1, target_y))

                # movement along finger direction
                foreground_pixels = np.argwhere(fg_mask == 255)

                if len(foreground_pixels) > 0:

                    px = foreground_pixels[:, 1] - fx
                    py = foreground_pixels[:, 0] - fy

                    projection = px * dx + py * dy
                    perpendicular = np.abs(px * dy - py * dx)

                    valid = (
                        (projection > 0) &
                        (perpendicular < 35)
                    )

                    candidates = foreground_pixels[valid]
                    candidate_projection = projection[valid]

                    if len(candidates) > 0:
                        furthest_idx = np.argmax(candidate_projection)
                        target_y, target_x = candidates[furthest_idx]

                        target_x = int(target_x)
                        target_y = int(target_y)

                    # GLOW BIT - Visual Only
    
                    glow_canvas = frame.copy()
                    laser_color = (0, 0, 255) # BGR Red

                    # outer flare (red blur)
                    cv2.line(glow_canvas, (fx, fy), (target_x, target_y), laser_color, 14)
                    cv2.circle(glow_canvas, (fx, fy), 18, laser_color, -1)
                    cv2.circle(glow_canvas, (target_x, target_y), 20, laser_color, -1)
                    glow_canvas = cv2.GaussianBlur(glow_canvas, (15, 15), 0)

                    # inner glow 
                    cv2.line(glow_canvas, (fx, fy), (target_x, target_y), laser_color, 6)
                    cv2.circle(glow_canvas, (fx, fy), 10, laser_color, -1)
                    cv2.circle(glow_canvas, (target_x, target_y), 12, laser_color, -1)

                    frame = cv2.addWeighted(glow_canvas, 0.35, frame, 0.65, 0)

                    # white line on top
                    white_core = (255, 255, 255)
                    cv2.line(frame, (fx, fy), (target_x, target_y), white_core, 2)
                    cv2.circle(frame, (fx, fy), 4, white_core, -1)
                    cv2.circle(frame, (target_x, target_y), 5, white_core, -1)
                else:
                    # target on index finger
                    cv2.circle(frame, (fx, fy), 8, (0, 0, 255), -1)
                    cv2.circle(frame, (fx, fy), 3, (255, 255, 255), -1)

        cv2.imshow('Glow Laser Pointer', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()

