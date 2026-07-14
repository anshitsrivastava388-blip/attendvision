"""
Entry point for the Smart Attendance Monitoring System.

Usage:
    python run.py
"""
import os
from app import create_app

env = os.environ.get("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    # use_reloader is forced off: the reloader re-execs the process in a
    # subprocess, which breaks OpenCV's cv2.imshow() GUI window on some
    # platforms (notably macOS) because the webcam preview must run on the
    # single "real" main thread of the process.
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=app.config["DEBUG"],
        use_reloader=False,
    )
