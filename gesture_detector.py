#!/usr/bin/env python3
"""Live hand tracking and basic gesture recognition with MediaPipe Tasks."""

from pathlib import Path
from urllib.request import urlretrieve
import time, socket

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

MODEL_PATH = Path(__file__).with_name("hand_landmarker.task")
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)

TIP_IDS = [4, 8, 12, 16, 20]
FINGER_NAMES = ["Thumb", "Index", "Middle", "Ring", "Pinky"]

# hand skeleton
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]

HOST = "127.0.0.1"
PORT = 7777

def ensure_model():
    """
    Download the official hand landmark model if it is not present.
    """
    if MODEL_PATH.exists():
        return

    try:
        urlretrieve(MODEL_URL, MODEL_PATH)
    except Exception:
        if MODEL_PATH.exists():
            MODEL_PATH.unlink()
        raise RuntimeError(
            "Could not download hand_landmarker.task. Check your internet "
            "connection and try again."
        )

def get_thumb_direction(landmarks):
    """
    Estimate thumb direction using the thumb tip and MCP joint.
    """
    thumb_tip = landmarks[4]
    thumb_mcp = landmarks[2]

    dx = thumb_tip.x - thumb_mcp.x
    dy = thumb_tip.y - thumb_mcp.y

    # estimate dominant direction
    if abs(dy) > abs(dx):
        if dy < 0:
            return "Thumbs up"
        else:
            return "Thumbs down"
    else:
        if dx < 0:
            return "Thumb left"
        else:
            return "Thumb right"

def count_fingers(landmarks, handedness):
    """
    Estimate which fingers are extended from normalized hand landmarks.
    """
    fingers = []

    # The camera image is mirrored. This thumb heuristic may need adjustment
    # depending on hand orientation and how the hand is held.
    if handedness == "Right":
        fingers.append(landmarks[4].x < landmarks[3].x)
    else:
        fingers.append(landmarks[4].x > landmarks[3].x)

    # For the four fingers, the tip is generally above the PIP joint when raised.
    for tip_id in TIP_IDS[1:]:
        pip_id = tip_id - 2
        fingers.append(landmarks[tip_id].y < landmarks[pip_id].y)

    return fingers


def recognize_gesture(fingers, landmarks):
    """
    Map a finger-extension pattern to a simple gesture label.
    """
    count = sum(fingers)


    # thumb direction
    if fingers[0] and count == 1:
        return get_thumb_direction(landmarks)

    # decrease volume
    if count == 0:
        return "Fist"

    # greet
    if count == 5:
        return "Open palm"

    # go to
    if fingers == [False, True, False, False, False]:
        return "Point"

    # play music
    if fingers == [False, True, True, False, False]:
        return "Peace"
    if fingers == [False, False, False, False, True]:
        return "Pinky finger"
    if fingers == [False, False, False, True, True]:
        return "Pinky and ring finger"

    return f"{count} finger(s) extended"


def draw_hand(frame, landmarks):
    """
    Draw landmark points and connecting lines on the webcam frame.
    """
    height, width = frame.shape[:2]
    points = [
        (int(lm.x * width), int(lm.y * height))
        for lm in landmarks
    ]
    for start, end in HAND_CONNECTIONS:
        cv2.line(
            frame, points[start], points[end],
            (180, 180, 180), 2, cv2.LINE_AA
        )

    for i, point in enumerate(points):
        radius = 6 if i in TIP_IDS else 4
        cv2.circle(frame, point, radius, (0, 220, 80), -1, cv2.LINE_AA)

def main():

    ensure_model()

    options = vision.HandLandmarkerOptions(
        base_options=python.BaseOptions(
            model_asset_path=str(MODEL_PATH)
        ),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    cap = cv2.VideoCapture(0)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("Could not open webcam.")
        return

    start_time = time.monotonic()
    last_timestamp_ms = -1

    last_sent_gesture = None

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:

            client_socket.connect((HOST, PORT))

            with vision.HandLandmarker.create_from_options(options) as detector:

                while True:

                    ret, frame = cap.read()

                    if not ret:
                        break

                    frame = cv2.flip(frame, 1)

                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    mp_image = mp.Image(
                        image_format=mp.ImageFormat.SRGB,
                        data=rgb
                    )

                    timestamp_ms = int(
                        (time.monotonic() - start_time) * 1000
                    )
                    timestamp_ms = max(
                        timestamp_ms,
                        last_timestamp_ms + 1
                    )

                    last_timestamp_ms = timestamp_ms

                    result = detector.detect_for_video(
                        mp_image,
                        timestamp_ms
                    )

                    current_gesture = "NONE"

                    if result.hand_landmarks:

                        landmarks = result.hand_landmarks[0]

                        handedness = "Unknown"

                        if result.handedness[0]:
                            handedness = (
                                result.handedness[0][0].category_name
                            )

                        draw_hand(frame, landmarks)

                        fingers = count_fingers(
                            landmarks,
                            handedness
                        )

                        gesture = recognize_gesture(fingers, landmarks)

                        current_gesture = (
                            f"{handedness}|{gesture}"
                        )

                        wrist_x = int(
                            landmarks[0].x * frame.shape[1]
                        )

                        wrist_y = int(
                            landmarks[0].y * frame.shape[0]
                        )

                        cv2.putText(
                            frame,
                            f"{handedness}: {gesture}",
                            (max(10, wrist_x - 70), max(25, wrist_y - 20)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (0, 220, 80),
                            2,
                            cv2.LINE_AA
                        )

                    # send when gesture changes
                    if current_gesture != last_sent_gesture:

                        message = f"gesture:{current_gesture}\n"

                        client_socket.sendall(message.encode())

                        print(f"Sent: {message.strip()}")

                        last_sent_gesture = current_gesture

                    cv2.putText(
                        frame,
                        "Q / Esc: quit",
                        (10, frame.shape[0] - 15),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 255),
                        1,
                        cv2.LINE_AA
                    )

                    cv2.imshow(
                        "Hand Gesture Recognition",
                        frame
                    )

                    key = cv2.waitKey(1) & 0xFF

                    if key in (ord("q"), ord("Q"), 27):
                        break

    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

