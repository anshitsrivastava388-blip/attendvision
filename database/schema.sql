-- Smart Attendance Monitoring System - Reference SQL schema
-- This mirrors the SQLAlchemy models in app/models.py.
-- Flask-SQLAlchemy creates these automatically on first run (db.create_all()),
-- this file is provided for reference / manual MySQL setup / documentation.

CREATE TABLE IF NOT EXISTS admins (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,   -- MySQL: INT AUTO_INCREMENT
    username        VARCHAR(80)  NOT NULL UNIQUE,
    email           VARCHAR(120) NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(20)  NOT NULL DEFAULT 'admin', -- admin | faculty
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subjects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            VARCHAR(120) NOT NULL,
    code            VARCHAR(20)  NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS students (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            VARCHAR(120) NOT NULL,
    roll_number     VARCHAR(40)  NOT NULL UNIQUE,
    department      VARCHAR(80)  NOT NULL,
    year            VARCHAR(20)  NOT NULL,
    section         VARCHAR(10)  NOT NULL,
    photo_path      VARCHAR(255),          -- relative path under static/uploads/students
    face_encoding   BLOB,                  -- pickled list[np.ndarray] of 128-d encodings
    is_face_trained BOOLEAN DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attendance (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL,
    subject_id      INTEGER,
    date            DATE NOT NULL,
    time            TIME NOT NULL,
    status          VARCHAR(10) NOT NULL DEFAULT 'Present', -- Present | Absent
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL,
    UNIQUE (student_id, date, subject_id) -- prevents duplicate attendance same day/subject
);

CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date);
CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id);
CREATE INDEX IF NOT EXISTS idx_students_dept ON students(department, year, section);
