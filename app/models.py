import pickle
from datetime import datetime, date as date_cls

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class Admin(UserMixin, db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="admin")  # admin | faculty
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)


class Subject(db.Model):
    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(20), nullable=False, unique=True)

    def __repr__(self):
        return f"<Subject {self.code}>"


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    roll_number = db.Column(db.String(40), nullable=False, unique=True)
    department = db.Column(db.String(80), nullable=False)
    year = db.Column(db.String(20), nullable=False)
    section = db.Column(db.String(10), nullable=False)
    photo_path = db.Column(db.String(255))  # relative to static/uploads/students
    face_encoding = db.Column(db.LargeBinary)  # pickled list[np.ndarray]
    is_face_trained = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    attendance_records = db.relationship(
        "Attendance", backref="student", cascade="all, delete-orphan", lazy="dynamic"
    )

    def set_encodings(self, encodings_list) -> None:
        """Store a list of 128-d numpy face encodings as a pickled blob."""
        self.face_encoding = pickle.dumps(encodings_list)
        self.is_face_trained = bool(encodings_list)

    def get_encodings(self):
        if not self.face_encoding:
            return []
        return pickle.loads(self.face_encoding)

    def attendance_percentage(self, total_working_days: int) -> float:
        if total_working_days <= 0:
            return 0.0
        present_days = self.attendance_records.filter_by(status="Present").count()
        return round((present_days / total_working_days) * 100, 2)

    def __repr__(self):
        return f"<Student {self.roll_number} {self.name}>"


class Attendance(db.Model):
    __tablename__ = "attendance"
    __table_args__ = (
        db.UniqueConstraint("student_id", "date", "subject_id", name="uq_attendance_once_per_day"),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    date = db.Column(db.Date, nullable=False, default=date_cls.today)
    time = db.Column(db.Time, nullable=False, default=lambda: datetime.now().time())
    status = db.Column(db.String(10), nullable=False, default="Present")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subject = db.relationship("Subject", backref="attendance_records")

    def __repr__(self):
        return f"<Attendance student={self.student_id} date={self.date} status={self.status}>"
