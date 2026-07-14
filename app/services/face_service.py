"""
Core AI logic: face capture, training (encoding), and real-time recognition.

Runs on the machine physically connected to the webcam (classroom PC).
Uses OpenCV for camera I/O + low-light enhancement, and the `face_recognition`
library (dlib HOG/CNN models) for detection and 128-d face encodings.

IMPORTANT (why there is no cv2.imshow here): a native OpenCV preview window
only works safely on a process's original "main" thread with a running GUI
event loop. Flask never guarantees that, and on macOS this reliably crashes
the whole interpreter (a hard Cocoa-level abort, not a catchable Python
exception) — happens even from a `multiprocessing` subprocess on newer macOS.

So instead we run the camera loop in a background thread with NO GUI window
at all, and stream the annotated frames to the browser as an MJPEG video feed
(`/…/feed` routes) — a normal, cross-platform way for a web app to show a
live camera preview. The browser page polls a `/…/status` endpoint for
progress (samples captured, students marked) and a `/…/stop` endpoint lets
the user end the session early.
"""
import os
import time
import threading
from datetime import datetime, date as date_cls

import cv2
import numpy as np
import face_recognition

from app.extensions import db
from app.models import Student, Attendance


class FaceServiceError(Exception):
    pass


def _enhance_low_light(frame):
    """Improve detection in dim classrooms via CLAHE histogram equalization."""
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l_enhanced = clahe.apply(l_channel)
    enhanced_lab = cv2.merge((l_enhanced, a_channel, b_channel))
    return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)


def _is_low_light(frame, threshold: int = 90) -> bool:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray)) < threshold


def _encode_jpeg(frame) -> bytes:
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    return buf.tobytes() if ok else b""


def mark_attendance(student: Student, subject_id=None) -> bool:
    """
    Inserts an attendance record for `student` for today, once only.
    Returns True if a new record was created, False if already marked today.
    """
    today = date_cls.today()
    existing = Attendance.query.filter_by(
        student_id=student.id, date=today, subject_id=subject_id
    ).first()
    if existing:
        return False

    record = Attendance(
        student_id=student.id,
        subject_id=subject_id,
        date=today,
        time=datetime.now().time(),
        status="Present",
    )
    db.session.add(record)
    db.session.commit()
    return True


# ---------------------------------------------------------------------------
# Shared session state: only one capture/recognition session runs at a time
# (there is only one physical webcam), so a single module-level object per
# session type is sufficient and keeps the Flask routes simple.
# ---------------------------------------------------------------------------

class _SessionState:
    def __init__(self):
        self.lock = threading.Lock()
        self.frame_lock = threading.Lock()
        self.reset()

    def reset(self):
        self.running = False
        self.done = False
        self.stop_requested = False
        self.error = None
        self.frame_bytes = None
        self.extra = {}


_capture_state = _SessionState()
_recognition_state = _SessionState()


# ---------------------------------------------------------------------------
# Face registration (capture + train)
# ---------------------------------------------------------------------------

def start_capture_session(app, student_id: int, camera_index: int, capture_count: int, upload_folder: str):
    with _capture_state.lock:
        if _capture_state.running:
            raise FaceServiceError("A face-registration session is already running.")
        _capture_state.reset()
        _capture_state.running = True
        _capture_state.extra = {"saved": 0, "capture_count": capture_count}

    thread = threading.Thread(
        target=_capture_loop,
        args=(app, student_id, camera_index, capture_count, upload_folder),
        daemon=True,
    )
    thread.start()


def _capture_loop(app, student_id, camera_index, capture_count, upload_folder):
    state = _capture_state
    with app.app_context():
        try:
            student = Student.query.get(student_id)
            if student is None:
                state.error = "Student not found."
                return

            student_dir = os.path.join(upload_folder, student.roll_number)
            os.makedirs(student_dir, exist_ok=True)

            cam = cv2.VideoCapture(camera_index)
            if not cam.isOpened():
                state.error = f"Could not open camera index {camera_index}. Check webcam connection."
                return

            encodings = []
            saved = 0
            try:
                while saved < capture_count and not state.stop_requested:
                    ok, frame = cam.read()
                    if not ok:
                        continue

                    if _is_low_light(frame):
                        frame = _enhance_low_light(frame)

                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    face_locations = face_recognition.face_locations(rgb_frame, model="hog")

                    display = frame.copy()
                    for (top, right, bottom, left) in face_locations:
                        cv2.rectangle(display, (left, top), (right, bottom), (0, 200, 0), 2)
                    cv2.putText(
                        display, f"Captured {saved}/{capture_count}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 0), 2,
                    )

                    with state.frame_lock:
                        state.frame_bytes = _encode_jpeg(display)

                    if len(face_locations) == 1:
                        face_encs = face_recognition.face_encodings(rgb_frame, face_locations)
                        if face_encs:
                            encodings.append(face_encs[0])
                            img_path = os.path.join(student_dir, f"{saved + 1}.jpg")
                            cv2.imwrite(img_path, frame)
                            saved += 1
                            state.extra["saved"] = saved
            finally:
                cam.release()

            if encodings:
                student.set_encodings(encodings)
                student.photo_path = f"{student.roll_number}/1.jpg"
                db.session.commit()
            state.extra["saved"] = saved
        except Exception as exc:
            state.error = str(exc)
        finally:
            state.running = False
            state.done = True
            db.session.remove()


def get_capture_status() -> dict:
    return {
        "running": _capture_state.running,
        "done": _capture_state.done,
        "error": _capture_state.error,
        "saved": _capture_state.extra.get("saved", 0),
        "capture_count": _capture_state.extra.get("capture_count", 0),
    }


def stop_capture_session():
    _capture_state.stop_requested = True


def capture_frame_generator():
    while True:
        with _capture_state.frame_lock:
            frame = _capture_state.frame_bytes
        if frame:
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        if not _capture_state.running and not frame:
            break
        time.sleep(0.05)
        if not _capture_state.running:
            # send a couple more frames then stop, so the browser gets the last one
            with _capture_state.frame_lock:
                frame = _capture_state.frame_bytes
            if frame:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            break


# ---------------------------------------------------------------------------
# Real-time attendance recognition
# ---------------------------------------------------------------------------

def start_recognition_session(app, camera_index: int, tolerance: float, subject_id=None):
    with _recognition_state.lock:
        if _recognition_state.running:
            raise FaceServiceError("An attendance session is already running.")
        _recognition_state.reset()
        _recognition_state.running = True
        _recognition_state.extra = {"marked": {}}

    thread = threading.Thread(
        target=_recognition_loop,
        args=(app, camera_index, tolerance, subject_id),
        daemon=True,
    )
    thread.start()


def _recognition_loop(app, camera_index, tolerance, subject_id):
    state = _recognition_state
    with app.app_context():
        try:
            students = Student.query.filter_by(is_face_trained=True).all()
            known_encodings, known_students = [], []
            for s in students:
                for enc in s.get_encodings():
                    known_encodings.append(enc)
                    known_students.append(s)

            if not known_encodings:
                state.error = "No trained faces found. Register students first."
                return

            cam = cv2.VideoCapture(camera_index)
            if not cam.isOpened():
                state.error = f"Could not open camera index {camera_index}. Check webcam connection."
                return

            marked = {}
            try:
                while not state.stop_requested:
                    ok, frame = cam.read()
                    if not ok:
                        continue

                    if _is_low_light(frame):
                        frame = _enhance_low_light(frame)

                    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                    rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                    face_locations = face_recognition.face_locations(rgb_small, model="hog")
                    face_encodings = face_recognition.face_encodings(rgb_small, face_locations)

                    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                        label = "Unknown"
                        color = (0, 0, 220)

                        distances = face_recognition.face_distance(known_encodings, face_encoding)
                        if len(distances) > 0:
                            best_idx = int(np.argmin(distances))
                            if distances[best_idx] <= tolerance:
                                matched_student = known_students[best_idx]
                                label = f"{matched_student.name} ({matched_student.roll_number})"
                                color = (0, 200, 0)

                                if matched_student.roll_number not in marked:
                                    created = mark_attendance(matched_student, subject_id=subject_id)
                                    marked[matched_student.roll_number] = {
                                        "name": matched_student.name,
                                        "roll_number": matched_student.roll_number,
                                        "newly_marked": created,
                                    }
                                    state.extra["marked"] = dict(marked)

                        top, right, bottom, left = top * 2, right * 2, bottom * 2, left * 2
                        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                        cv2.putText(
                            frame, label, (left, top - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2,
                        )

                    cv2.putText(
                        frame, f"Marked today: {len(marked)}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2,
                    )

                    with state.frame_lock:
                        state.frame_bytes = _encode_jpeg(frame)
            finally:
                cam.release()
        except Exception as exc:
            state.error = str(exc)
        finally:
            state.running = False
            state.done = True
            db.session.remove()


def get_recognition_status() -> dict:
    return {
        "running": _recognition_state.running,
        "done": _recognition_state.done,
        "error": _recognition_state.error,
        "marked": _recognition_state.extra.get("marked", {}),
    }


def stop_recognition_session():
    _recognition_state.stop_requested = True


def recognition_frame_generator():
    while True:
        with _recognition_state.frame_lock:
            frame = _recognition_state.frame_bytes
        if frame:
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        if not _recognition_state.running and not frame:
            break
        time.sleep(0.05)
        if not _recognition_state.running:
            with _recognition_state.frame_lock:
                frame = _recognition_state.frame_bytes
            if frame:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            break
