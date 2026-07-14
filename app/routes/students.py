import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Student

students_bp = Blueprint("students", __name__, url_prefix="/students")


@students_bp.route("/")
@login_required
def list_students():
    query = Student.query

    search = request.args.get("q", "").strip()
    department = request.args.get("department", "")
    year = request.args.get("year", "")
    section = request.args.get("section", "")

    if search:
        query = query.filter(
            (Student.name.ilike(f"%{search}%")) | (Student.roll_number.ilike(f"%{search}%"))
        )
    if department:
        query = query.filter_by(department=department)
    if year:
        query = query.filter_by(year=year)
    if section:
        query = query.filter_by(section=section)

    students = query.order_by(Student.roll_number).all()
    departments = [row[0] for row in db.session.query(Student.department).distinct()]

    return render_template(
        "students/list.html",
        students=students,
        departments=departments,
        search=search,
        department=department,
        year=year,
        section=section,
    )


@students_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_student():
    if request.method == "POST":
        roll_number = request.form.get("roll_number", "").strip()
        if Student.query.filter_by(roll_number=roll_number).first():
            flash("A student with this roll number already exists.", "danger")
            return redirect(url_for("students.add_student"))

        student = Student(
            name=request.form.get("name", "").strip(),
            roll_number=roll_number,
            department=request.form.get("department", "").strip(),
            year=request.form.get("year", "").strip(),
            section=request.form.get("section", "").strip(),
        )

        photo = request.files.get("photo")
        if photo and photo.filename:
            student_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], roll_number)
            os.makedirs(student_dir, exist_ok=True)
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(student_dir, filename))
            student.photo_path = f"{roll_number}/{filename}"

        db.session.add(student)
        db.session.commit()
        flash(f"Student '{student.name}' added. Next, register their face.", "success")
        return redirect(url_for("face.register_face", student_id=student.id))

    return render_template("students/add.html")


@students_bp.route("/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)

    if request.method == "POST":
        student.name = request.form.get("name", "").strip()
        student.department = request.form.get("department", "").strip()
        student.year = request.form.get("year", "").strip()
        student.section = request.form.get("section", "").strip()

        new_roll = request.form.get("roll_number", "").strip()
        if new_roll != student.roll_number:
            if Student.query.filter_by(roll_number=new_roll).first():
                flash("Roll number already in use by another student.", "danger")
                return redirect(url_for("students.edit_student", student_id=student.id))
            student.roll_number = new_roll

        photo = request.files.get("photo")
        if photo and photo.filename:
            student_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], student.roll_number)
            os.makedirs(student_dir, exist_ok=True)
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(student_dir, filename))
            student.photo_path = f"{student.roll_number}/{filename}"

        db.session.commit()
        flash("Student updated successfully.", "success")
        return redirect(url_for("students.list_students"))

    return render_template("students/edit.html", student=student)


@students_bp.route("/<int:student_id>/delete", methods=["POST"])
@login_required
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    db.session.delete(student)
    db.session.commit()
    flash(f"Student '{student.name}' deleted.", "info")
    return redirect(url_for("students.list_students"))
