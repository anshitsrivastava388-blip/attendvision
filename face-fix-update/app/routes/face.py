from flask import Blueprint, render_template, redirect, url_for, flash, current_app, request, jsonify, Response
from flask_login import login_required

from app.models import Student, Subject
from app.services.face_service import (
    start_capture_session,
    get_capture_status,
    stop_capture_session,
    capture_frame_generator,
    start_recognition_session,
    get_recognition_status,
    stop_recognition_session,
    recognition_frame_generator,
    FaceServiceError,
)

face_bp = Blueprint("face", __name__)


# ---------------------------------------------------------------------------
# Face registration (capture + train)
# ---------------------------------------------------------------------------

@face_bp.route("/students/<int:student_id>/register-face", methods=["GET"])
@login_required
def register_face(student_id):
    student = Student.query.get_or_404(student_id)
    return render_template("students/register_face.html", student=student)


@face_bp.route("/students/<int:student_id>/register-face/start", methods=["POST"])
@login_required
def register_face_start(student_id):
    student = Student.query.get_or_404(student_id)
    try:
        start_capture_session(
            current_app._get_current_object(),
            student_id=student.id,
            camera_index=current_app.config["CAMERA_INDEX"],
            capture_count=current_app.config["FACE_CAPTURE_COUNT"],
            upload_folder=current_app.config["UPLOAD_FOLDER"],
        )
        return jsonify({"ok": True})
    except FaceServiceError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 409


@face_bp.route("/students/<int:student_id>/register-face/stop", methods=["POST"])
@login_required
def register_face_stop(student_id):
    stop_capture_session()
    return jsonify({"ok": True})


@face_bp.route("/students/<int:student_id>/register-face/status", methods=["GET"])
@login_required
def register_face_status(student_id):
    return jsonify(get_capture_status())


@face_bp.route("/students/<int:student_id>/register-face/feed", methods=["GET"])
@login_required
def register_face_feed(student_id):
    return Response(capture_frame_generator(), mimetype="multipart/x-mixed-replace; boundary=frame")


# ---------------------------------------------------------------------------
# Real-time attendance recognition
# ---------------------------------------------------------------------------

@face_bp.route("/attendance/start", methods=["GET"])
@login_required
def start_attendance():
    subjects = Subject.query.order_by(Subject.name).all()
    return render_template("attendance/start.html", subjects=subjects, camera_status="ready")


@face_bp.route("/attendance/start/begin", methods=["POST"])
@login_required
def attendance_begin():
    subject_id = request.form.get("subject_id") or None
    try:
        start_recognition_session(
            current_app._get_current_object(),
            camera_index=current_app.config["CAMERA_INDEX"],
            tolerance=current_app.config["FACE_MATCH_TOLERANCE"],
            subject_id=int(subject_id) if subject_id else None,
        )
        return jsonify({"ok": True})
    except FaceServiceError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 409


@face_bp.route("/attendance/start/stop", methods=["POST"])
@login_required
def attendance_stop():
    stop_recognition_session()
    return jsonify({"ok": True})


@face_bp.route("/attendance/start/status", methods=["GET"])
@login_required
def attendance_status():
    return jsonify(get_recognition_status())


@face_bp.route("/attendance/start/feed", methods=["GET"])
@login_required
def attendance_feed():
    return Response(recognition_frame_generator(), mimetype="multipart/x-mixed-replace; boundary=frame")
