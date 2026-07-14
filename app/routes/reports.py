from datetime import date, timedelta
from calendar import monthrange

from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.models import Attendance, Student
from app.services.email_service import email_attendance_report
from app.routes.attendance import _filtered_query

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/")
@login_required
def reports_page():
    total_students = Student.query.count()
    total_present = Attendance.query.filter_by(status="Present").count()
    total_days_logged = db.session.query(func.count(func.distinct(Attendance.date))).scalar() or 0
    overall_pct = (
        round((total_present / (total_students * total_days_logged)) * 100, 2)
        if total_students and total_days_logged
        else 0.0
    )

    return render_template(
        "reports/reports.html",
        total_students=total_students,
        total_present=total_present,
        total_days_logged=total_days_logged,
        overall_pct=overall_pct,
    )


@reports_bp.route("/api/monthly")
@login_required
def api_monthly():
    """Chart.js data: attendance count per day for the current month."""
    today = date.today()
    _, days_in_month = monthrange(today.year, today.month)
    month_start = today.replace(day=1)
    month_end = today.replace(day=days_in_month)

    # Use a plain date-range filter (not strftime) so this works on both
    # SQLite and MySQL without dialect-specific SQL functions.
    rows = (
        db.session.query(Attendance.date, func.count(Attendance.id))
        .filter(
            Attendance.status == "Present",
            Attendance.date >= month_start,
            Attendance.date <= month_end,
        )
        .group_by(Attendance.date)
        .all()
    )
    counts_by_day = {r[0].day: r[1] for r in rows}
    labels = [str(d) for d in range(1, days_in_month + 1)]
    data = [counts_by_day.get(d, 0) for d in range(1, days_in_month + 1)]

    return jsonify({"labels": labels, "data": data})


@reports_bp.route("/api/department")
@login_required
def api_department():
    """Chart.js data: present-count by department for today."""
    today = date.today()
    rows = (
        db.session.query(Student.department, func.count(Attendance.id))
        .join(Attendance, Attendance.student_id == Student.id)
        .filter(Attendance.date == today, Attendance.status == "Present")
        .group_by(Student.department)
        .all()
    )
    return jsonify({"labels": [r[0] for r in rows], "data": [r[1] for r in rows]})


@reports_bp.route("/email", methods=["POST"])
@login_required
def email_report():
    recipients_raw = request.form.get("recipients", "")
    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]
    records_list = _filtered_query().all()

    try:
        email_attendance_report(recipients, records_list, subject="Weekly Attendance Report")
        flash(f"Report emailed to: {', '.join(recipients)}", "success")
    except Exception as exc:  # noqa: BLE001 - surface any mail/config error to the admin
        flash(f"Failed to send email: {exc}", "danger")

    return redirect(url_for("attendance.records"))
