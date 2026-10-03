import os

from flask import Blueprint, Flask

from dashboard.config import Config


def create_app(user_data_path=None):
    app = Flask(__name__)

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

    return app
