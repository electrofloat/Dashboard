import hashlib
import logging
import os

from flask import Blueprint, Flask, request

from dashboard.config import ConfigReloader

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


def css_string(value):
    safe = "/:.-_?=&%#~+,;@!$*"
    escaped = "".join(c if c.isalnum() or c in safe else f"\\{ord(c):x} " for c in str(value))
    return f'"{escaped}"'


def set_security_headers(response):
    response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    return response


def add_static_versions(app):
    versions = {}

    @app.url_defaults
    def static_version(endpoint, values):
        if endpoint != "static" or "filename" not in values:
            return
        path = os.path.join(app.static_folder, values["filename"])
        try:
            mtime = os.stat(path).st_mtime_ns
        except OSError:
            return
        cached = versions.get(path)
        if not cached or cached[0] != mtime:
            with open(path, "rb") as f:
                cached = (mtime, hashlib.sha256(f.read()).hexdigest()[:12])
            versions[path] = cached
        values["v"] = cached[1]

    @app.after_request
    def cache_versioned_static(response):
        if request.endpoint == "static" and "v" in request.args and response.status_code == 200:
            response.cache_control.no_cache = None
            response.cache_control.public = True
            response.cache_control.max_age = 31536000
            response.cache_control.immutable = True
        return response


def create_app(user_data_path=None):
    app = Flask(__name__)

    if not user_data_path:
        user_data_path = os.environ.get("DASHBOARD_USER_DATA") or os.path.join(app.root_path, "..", "user-data")
    user_data_path = os.path.abspath(user_data_path)

    logger = logging.getLogger("dashboard")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    app.extensions["dashboard.config"] = ConfigReloader(app.root_path, user_data_path)

    from dashboard.main import main as main_blueprint

    app.register_blueprint(main_blueprint)

    blueprint = Blueprint(
        "userdata",
        __name__,
        static_url_path="/static/userdata",
        static_folder=user_data_path,
    )
    app.register_blueprint(blueprint)

    add_static_versions(app)
    app.after_request(set_security_headers)
    app.jinja_env.filters["css_string"] = css_string

    return app
