from flask import Flask, Blueprint


def create_app():
    app = Flask(__name__)

    from .main import main as main_blueprint

    app.register_blueprint(main_blueprint)

    blueprint = Blueprint("userdata", __name__, static_url_path="/static/userdata", static_folder="../user-data")
    app.register_blueprint(blueprint)

    return app
