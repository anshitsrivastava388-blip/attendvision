# Deployment Guide

## Important: Camera Hardware Constraint

The face registration and smart attendance modules use OpenCV to open a **physical webcam attached
to the machine running the Flask process** (`cv2.VideoCapture` + `cv2.imshow`). This means:

- The Flask server must run **on-premise**, on a PC physically connected to a webcam in the classroom/lab.
- It is **not** designed to run on a remote cloud server where "the camera" would actually be a browser's
  camera on a different machine. If you need browser-based (remote) camera capture instead of a local
  server-attached webcam, the capture/recognition logic in `app/services/face_service.py` would need to
  be reworked to accept image frames uploaded from the browser (via `getUserMedia` + `fetch`) rather than
  calling `cv2.VideoCapture` directly. This is a meaningful architecture change, not a config change.
- Everything else (dashboard, student management, records, reports, exports, email) is a normal Flask web
  app and can be deployed however you like.

## Recommended: Single classroom/lab PC (most common setup)

1. Install Python + dependencies as per `INSTALLATION.md` directly on the lab PC with the webcam.
2. Run with a production WSGI server instead of the Flask dev server:
   ```bash
   pip install waitress   # Windows-friendly production server
   waitress-serve --listen=0.0.0.0:5000 run:app
   ```
   On Linux/macOS you can use gunicorn instead (note: gunicorn's default worker model does not suit
   long-blocking camera sessions well — keep `--workers 1 --threads 4` and expect the recognition
   request to block that worker until the admin presses `q`):
   ```bash
   pip install gunicorn
   gunicorn -w 1 --threads 4 -b 0.0.0.0:5000 run:app
   ```
3. Make it start automatically:
   - **Windows**: create a Scheduled Task or a `.bat` shortcut in the Startup folder that activates the
     venv and runs the server command.
   - **Linux**: create a `systemd` service unit that runs the same command on boot.
4. Other staff on the same network/Wi-Fi can open `http://<lab-pc-ip>:5000` in their browser to view
   dashboards, records, and reports — only the PC with the webcam needs to be used for the actual
   face registration / attendance capture pages.

## Database for multi-room / multi-PC colleges

If multiple classroom PCs each run their own camera capture but should share one attendance database:

1. Set up a central MySQL server (a small VM or on-prem server is enough).
2. Point every PC's `.env` `DATABASE_URL` at that same MySQL instance:
   ```
   DATABASE_URL=mysql+pymysql://attendance_user:password@<mysql-server-ip>:3306/attendance_db
   ```
3. Each classroom PC still needs its own webcam and its own running Flask process (for the camera
   access), but they all read/write the same central database, so dashboards/reports show
   institution-wide data.

## Backups

- SQLite: back up the `instance/attendance.db` file on a schedule (cron / Task Scheduler).
- MySQL: use `mysqldump` on a schedule:
  ```bash
  mysqldump -u attendance_user -p attendance_db > backup_$(date +%F).sql
  ```
- Also back up `app/static/uploads/students/` (student photos) alongside the database.

## Security checklist before going live

- Set a strong, random `FLASK_SECRET_KEY`.
- Change the default admin password immediately after first login.
- Set `FLASK_DEBUG=0` in production.
- Put the app behind HTTPS if accessed over a network beyond a trusted local LAN (e.g. via nginx as
  a reverse proxy with a TLS certificate).
- Restrict who has physical/network access to the camera-capture pages — anyone who can trigger
  "Start Attendance Session" can mark students present.
