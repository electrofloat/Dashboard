import os

from flask import Blueprint, Flask

from dashboard.config import Config

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "font-src 'self'",
        "img-src * data:",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)


def set_security_headers(response):
    response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    return response


def create_app(user_data_path=None):
    app = Flask(__name__)
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 3600

    if not user_data_path:
        user_data_path = os.environ.get("DASHBOARD_USER_DATA") or os.path.join(app.root_path, "..", "user-data")
    user_data_path = os.path.abspath(user_data_path)

    config = Config(app.root_path, user_data_path)
    error = config.load()
    if error:
        error = f"Error opening config.yml; error='{error}'"
        app.logger.error(error)
    app.extensions["dashboard.config"] = config
    app.extensions["dashboard.error"] = error

    from dashboard.main import main as main_blueprint

    app.register_blueprint(main_blueprint)

    blueprint = Blueprint(
        "userdata",
        __name__,
        static_url_path="/static/userdata",
        static_folder=user_data_path,
    )
    app.register_blueprint(blueprint)

    app.after_request(set_security_headers)

    return app
