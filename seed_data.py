"""
Populates the database with sample data for demo/testing purposes:
- A default admin (also created automatically on first run)
- A handful of subjects
- Sample students (without trained face encodings - use the
  "Register Face" page with a real webcam to train them)
- A few sample attendance records over the past week

Usage:
    python seed_data.py
"""
import random
from datetime import date, timedelta, time

from app import create_app
from app.extensions import db
from app.models import Admin, Student, Subject, Attendance

SAMPLE_STUDENTS = [
    ("Aarav Sharma", "CS21B001", "Computer Science", "3rd Year", "A"),
    ("Diya Patel", "CS21B002", "Computer Science", "3rd Year", "A"),
    ("Rohan Gupta", "CS21B003", "Computer Science", "3rd Year", "B"),
    ("Ananya Iyer", "EC21B010", "Electronics", "3rd Year", "A"),
    ("Vikram Nair", "EC21B011", "Electronics", "3rd Year", "B"),
    ("Sneha Reddy", "ME21B020", "Mechanical", "2nd Year", "A"),
    ("Karan Mehta", "ME21B021", "Mechanical", "2nd Year", "B"),
    ("Priya Singh", "CE21B030", "Civil", "2nd Year", "A"),
]

SAMPLE_SUBJECTS = [
    ("Data Structures", "CS201"),
    ("Digital Electronics", "EC205"),
    ("Thermodynamics", "ME210"),
    ("Structural Analysis", "CE220"),
]


def run():
    app = create_app("development")
    with app.app_context():
        db.create_all()

        if Admin.query.count() == 0:
            admin = Admin(
                username=app.config["DEFAULT_ADMIN_USERNAME"],
                email=app.config["DEFAULT_ADMIN_EMAIL"],
                role="admin",
            )
            admin.set_password(app.config["DEFAULT_ADMIN_PASSWORD"])
            db.session.add(admin)

        subjects = {}
        for name, code in SAMPLE_SUBJECTS:
            subj = Subject.query.filter_by(code=code).first()
            if not subj:
                subj = Subject(name=name, code=code)
                db.session.add(subj)
            subjects[code] = subj

        db.session.commit()

        students = []
        for name, roll, dept, year, section in SAMPLE_STUDENTS:
            student = Student.query.filter_by(roll_number=roll).first()
            if not student:
                student = Student(
                    name=name, roll_number=roll, department=dept, year=year, section=section
                )
                db.session.add(student)
            students.append(student)
        db.session.commit()

        # Sample attendance for the last 7 days (skips weekends), random presence per subject
        today = date.today()
        for offset in range(7, 0, -1):
            day = today - timedelta(days=offset)
            if day.weekday() >= 5:
                continue
            for student in students:
                if random.random() < 0.85:  # ~85% attendance rate
                    subj = random.choice(list(subjects.values()))
                    exists = Attendance.query.filter_by(
                        student_id=student.id, date=day, subject_id=subj.id
                    ).first()
                    if not exists:
                        db.session.add(Attendance(
                            student_id=student.id,
                            subject_id=subj.id,
                            date=day,
                            time=time(hour=random.randint(8, 11), minute=random.randint(0, 59)),
                            status="Present",
                        ))
        db.session.commit()
        print("Sample data seeded successfully.")
        print(f"Login with: {app.config['DEFAULT_ADMIN_USERNAME']} / {app.config['DEFAULT_ADMIN_PASSWORD']}")


if __name__ == "__main__":
    run()
