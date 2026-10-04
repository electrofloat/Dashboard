import hashlib
import logging
import os

from flask import Blueprint, Flask, request
from werkzeug.security import safe_join

from dashboard.config import Config, ConfigReloader

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


def add_static_versions(app, user_data_path):
    versions = {}

    def file_version(folder, filename):
        path = safe_join(folder, filename)
        if not path:
            return None
        try:
            mtime = os.stat(path).st_mtime_ns
        except OSError:
            return None
        cached = versions.get(path)
        if not cached or cached[0] != mtime:
            with open(path, "rb") as f:
                cached = (mtime, hashlib.sha256(f.read()).hexdigest()[:12])
            versions[path] = cached
        return cached[1]

    @app.url_defaults
    def static_version(endpoint, values):
        if endpoint != "static" or "filename" not in values:
            return
        version = file_version(app.static_folder, values["filename"])
        if version:
            values["v"] = version

    # The background and the icons come from config.yml as plain /static/... urls instead of url_for()
    def versioned(url):
        if not url:
            return url
        if url.startswith(Config.USERDATA_URL):
            version = file_version(user_data_path, url[len(Config.USERDATA_URL) :])
        elif url.startswith(Config.STATIC_URL):
            version = file_version(app.static_folder, url[len(Config.STATIC_URL) :])
        else:
            return url
        return f"{url}?v={version}" if version else url

    app.jinja_env.filters["versioned"] = versioned

    @app.after_request
    def cache_versioned_static(response):
        if request.endpoint in ("static", "userdata.static") and "v" in request.args and response.status_code == 200:
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

    add_static_versions(app, user_data_path)
    app.after_request(set_security_headers)
    app.jinja_env.filters["css_string"] = css_string

    return app
