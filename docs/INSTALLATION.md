# Installation Guide

## 1. Prerequisites

- Python 3.10 or 3.11 (dlib/face_recognition wheels are most reliable on these versions)
- A webcam connected to the PC that will run face registration / attendance capture
- Windows, macOS, or Linux
- (Windows only) Visual Studio Build Tools with the "Desktop development with C++" workload — required to compile `dlib`
- (Linux only) `cmake`, `build-essential`, `libopenblas-dev` for `dlib`:
  ```bash
  sudo apt update
  sudo apt install -y cmake build-essential libopenblas-dev liblapack-dev
  ```

## 2. Get the code

Copy the `smart-attendance-system/` folder to the machine that will run it.

## 3. Create a virtual environment

```bash
cd smart-attendance-system
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

## 4. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

If `dlib` fails to build from source, install a prebuilt wheel instead:

```bash
pip install cmake
pip install dlib --no-cache-dir
```

## 5. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:
- `FLASK_SECRET_KEY` — set a long random string
- `DATABASE_URL` — leave as SQLite for a single-PC setup, or point to MySQL (see below)
- `DEFAULT_ADMIN_USERNAME` / `DEFAULT_ADMIN_PASSWORD` — first-login credentials (change password after login)
- `MAIL_*` — only needed if you want the "Email Report" feature to work
- `CAMERA_INDEX` — usually `0` for the default/built-in webcam; try `1`, `2`, ... if you have multiple cameras

## 6. (Optional) Switch to MySQL

```sql
CREATE DATABASE attendance_db CHARACTER SET utf8mb4;
CREATE USER 'attendance_user'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON attendance_db.* TO 'attendance_user'@'localhost';
FLUSH PRIVILEGES;
```

Then in `.env`:
```
DATABASE_URL=mysql+pymysql://attendance_user:password@localhost:3306/attendance_db
```

`database/schema.sql` is provided for reference if you prefer to create tables manually; by default the app creates them automatically on first run.

## 7. Seed sample data (optional, for demo/testing)

```bash
python seed_data.py
```

This creates the default admin, a few subjects, sample students, and a week of sample attendance history. Sample students have no trained face encodings — you must register real faces via the webcam for face recognition to work with real people.

## 8. Run the app

```bash
python run.py
```

Open `http://localhost:5000` in a browser on the same machine and log in with the admin credentials from `.env`.

## 9. First-time workflow

1. Log in.
2. Go to **Students → Add Student**, fill in details, save.
3. You're redirected to **Face Registration** — click "Start Camera & Capture" and let the student face the webcam; ~30 samples are captured and encoded automatically.
4. Repeat for each student.
5. Go to **Smart Attendance → Start Attendance Session** to begin real-time recognition; recognized students are marked present automatically, once per day.
6. View **Attendance Records** and **Reports & Analytics** for history, filters, exports, and charts.
