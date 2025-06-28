from flask import Flask, request, Blueprint, render_template, abort, make_response
import os

from dashboard.config import Config

main = Blueprint('main', __name__)
user_data_path = None
global_error = None
config = None

def get_global_error_response():
    response = make_response(global_error, 200)
    response.mimetype = "text/plain"

    return response

def get_request_headers():
    request_headers = {}
    request_headers["authelia_session"] = request.cookies.get("authelia_session")
    request_headers["x_forwarded_for"] = request.headers.get("X-Forwarded-For")
    request_headers["remote_user"] = request.headers.get("Remote-User")
    request_headers["remote_groups"] = request.headers.get("Remote-Groups")

    if "FLASK_DEBUG" in os.environ:
      request_headers["x_forwarded_for"] = "10.0.0.1"
      request_headers["remote_user"] = "testuser"
      request_headers["remote_groups"] = "testgroup1,testgroup2"

    return request_headers

@main.route("/")
def index():
    if global_error:
      return get_global_error_response()

    request_headers = get_request_headers()
    conf = config.get_template_config(request_headers)

    return render_template('index.html', config = conf)

@main.route("/color")
def route_color():
    if global_error:
      return get_global_error_response()

    request_headers = get_request_headers()

    if not config.is_settings_allowed(request_headers):
      abort(401, description="")

    return render_template('color.html', background_img = config.get_background_img())

app = Flask(__name__)
with app.app_context():
    user_data_path = os.path.abspath(os.path.join(app.root_path, '..', 'user-data'))
    if "FLASK_DEBUG" in os.environ:
      user_data_path = "."
    config = Config(app.root_path, user_data_path)
    error = config.load()
    if error:
      global_error = f"Error opening config.yml; error={error}"
      print(global_error)
