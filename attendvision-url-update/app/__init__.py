import os
from flask import Flask

from config import config_by_name
from app.extensions import db, login_manager, mail


def create_app(env: str = "development") -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_by_name.get(env, config_by_name["development"]))

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    from app.models import Admin

    @login_manager.user_loader
    def load_user(user_id):
        return Admin.query.get(int(user_id))

    # Blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.students import students_bp
    from app.routes.face import face_bp
    from app.routes.attendance import attendance_bp
    from app.routes.reports import reports_bp

    url_prefix = "/attendvision"
    app.register_blueprint(auth_bp, url_prefix=url_prefix)
    app.register_blueprint(dashboard_bp, url_prefix=url_prefix)
    app.register_blueprint(students_bp, url_prefix=url_prefix)
    app.register_blueprint(face_bp, url_prefix=url_prefix)
    app.register_blueprint(attendance_bp, url_prefix=url_prefix)
    app.register_blueprint(reports_bp, url_prefix=url_prefix)

    @app.route("/")
    def _root_redirect():
        from flask import redirect, url_for
        return redirect(url_for("dashboard.index"))

    with app.app_context():
        db.create_all()
        _bootstrap_default_admin(app)

    @app.context_processor
    def inject_globals():
        from datetime import datetime as _dt
        return {"current_year": _dt.now().year}

    return app


def _bootstrap_default_admin(app: Flask) -> None:
    """Create a default admin account on first run if none exists."""
    from app.models import Admin

    if Admin.query.count() == 0:
        admin = Admin(
            username=app.config["DEFAULT_ADMIN_USERNAME"],
            email=app.config["DEFAULT_ADMIN_EMAIL"],
            role="admin",
        )
        admin.set_password(app.config["DEFAULT_ADMIN_PASSWORD"])
        db.session.add(admin)
        db.session.commit()
        app.logger.info(
            "Created default admin '%s' - change this password immediately.",
            app.config["DEFAULT_ADMIN_USERNAME"],
        )
