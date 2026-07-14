from datetime import date

from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.models import Student, Attendance, Subject

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def index():
    today = date.today()

    total_students = Student.query.count()
    present_today = Attendance.query.filter_by(date=today, status="Present").count()
    absent_today = max(total_students - present_today, 0)
    attendance_pct_today = round((present_today / total_students) * 100, 1) if total_students else 0.0
    total_subjects = Subject.query.count()

    dept_rows = (
        db.session.query(Student.department, func.count(Student.id))
        .group_by(Student.department)
        .all()
    )
    department_labels = [row[0] for row in dept_rows]
    department_counts = [row[1] for row in dept_rows]

    recent = (
        Attendance.query.order_by(Attendance.created_at.desc()).limit(8).all()
    )

    return render_template(
        "dashboard.html",
        total_students=total_students,
        present_today=present_today,
        absent_today=absent_today,
        attendance_pct_today=attendance_pct_today,
        total_subjects=total_subjects,
        department_labels=department_labels,
        department_counts=department_counts,
        recent=recent,
        today=today,
    )
