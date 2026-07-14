from datetime import datetime

from flask import Blueprint, render_template, request, send_file
from flask_login import login_required

from app.models import Attendance, Student, Subject
from app.services.export_service import export_to_csv, export_to_excel

attendance_bp = Blueprint("attendance", __name__, url_prefix="/attendance")


def _filtered_query():
    query = Attendance.query.join(Student)

    date_str = request.args.get("date", "")
    student_q = request.args.get("student", "").strip()
    subject_id = request.args.get("subject_id", "")
    department = request.args.get("department", "")
    status = request.args.get("status", "")

    if date_str:
        try:
            day = datetime.strptime(date_str, "%Y-%m-%d").date()
            query = query.filter(Attendance.date == day)
        except ValueError:
            pass
    if student_q:
        query = query.filter(
            (Student.name.ilike(f"%{student_q}%")) | (Student.roll_number.ilike(f"%{student_q}%"))
        )
    if subject_id:
        query = query.filter(Attendance.subject_id == int(subject_id))
    if department:
        query = query.filter(Student.department == department)
    if status:
        query = query.filter(Attendance.status == status)

    return query.order_by(Attendance.date.desc(), Attendance.time.desc())


@attendance_bp.route("/records")
@login_required
def records():
    records_list = _filtered_query().all()
    subjects = Subject.query.order_by(Subject.name).all()
    departments = [row[0] for row in Student.query.with_entities(Student.department).distinct()]

    return render_template(
        "attendance/records.html",
        records=records_list,
        subjects=subjects,
        departments=departments,
        filters=request.args,
    )


@attendance_bp.route("/export/<fmt>")
@login_required
def export(fmt):
    records_list = _filtered_query().all()

    if fmt == "csv":
        buf = export_to_csv(records_list)
        return send_file(buf, mimetype="text/csv", as_attachment=True, download_name="attendance.csv")
    if fmt == "excel":
        buf = export_to_excel(records_list)
        return send_file(
            buf,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="attendance.xlsx",
        )
    return "Unsupported format", 400
