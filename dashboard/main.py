import os

from flask import (
    Blueprint,
    Response,
    abort,
    copy_current_request_context,
    current_app,
    make_response,
    render_template,
    request,
)

main = Blueprint("main", __name__)


def get_config():
    return current_app.extensions["dashboard.config"]


def get_global_error():
    return current_app.extensions["dashboard.error"]


def get_global_error_response():
    response = make_response(get_global_error(), 200)
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
    if get_global_error():
        return get_global_error_response()

    config = get_config()
    request_headers = get_request_headers()
    conf = config.get_app_config(request_headers)

    return render_template("index.html", config=conf)


@main.route("/folder", defaults={"subpath": ""})
@main.route("/folder/<path:subpath>")
def route_folder(subpath):
    if get_global_error():
        return get_global_error_response()

    config = get_config()
    if (not subpath) or (not config.get_tiles_on_path(subpath.split("/"))):
        abort(404)

    request_headers = get_request_headers()
    conf = config.get_app_config(request_headers)

    return render_template("index.html", config=conf, subpath=subpath)


@main.route("/stream-tiles/", defaults={"subpath": ""})
@main.route("/stream-tiles/<path:subpath>")
def route_stream_tiles(subpath):
    config = get_config()
    request_headers = get_request_headers()

    @copy_current_request_context
    def render_tile_cb(index, tile):
        html = render_template("tile_fragment.html", tile=tile)
        safe_html = html.replace('"', '\\"').replace("\n", "")
        return {"id": index, "html": safe_html}

    def generate():
        for result in config.stream_active_tiles(subpath, request_headers, render_tile_cb):
            yield f'data: {{"id": {result["id"]}, "html": "{result["html"]}"}}\n\n'

        yield 'data: {"done": true}\n\n'

    if subpath and (not config.get_tiles_on_path(subpath.split("/"))):
        abort(404)
    return Response(generate(), mimetype="text/event-stream")


@main.route("/color")
def route_color():
    if get_global_error():
        return get_global_error_response()

    config = get_config()
    request_headers = get_request_headers()

    if not config.is_settings_allowed(request_headers):
        abort(401, description="")

    conf = config.get_app_config(request_headers)
    return render_template("color.html", config=conf)
