import json

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    make_response,
    render_template,
    request,
    stream_with_context,
    url_for,
)

from dashboard.auth import dev_fake_auth

main = Blueprint("main", __name__)


def get_config():
    return current_app.extensions["dashboard.config"]


@main.before_request
def check_global_error():
    if current_app.extensions["dashboard.error"]:
        response = make_response("Dashboard configuration error, see the server logs for details.", 500)
        response.mimetype = "text/plain"
        return response


def get_request_headers(config):
    request_headers = {}
    request_headers["authelia_session"] = request.cookies.get(config.authelia_cookie_name)

    remote_addr = request.remote_addr
    if config.is_peer_trusted(remote_addr):
        request_headers["x_forwarded_for"] = config.get_client_ip(remote_addr, request.headers.get("X-Forwarded-For"))
        request_headers["remote_user"] = request.headers.get("Remote-User")
        request_headers["remote_groups"] = request.headers.get("Remote-Groups")
    else:
        # The request did not come through a trusted proxy, so the identity headers may be forged
        request_headers["x_forwarded_for"] = remote_addr
        request_headers["remote_user"] = None
        request_headers["remote_groups"] = None

    if dev_fake_auth():
        request_headers["x_forwarded_for"] = "10.0.0.1"
        request_headers["remote_user"] = "testuser"
        request_headers["remote_groups"] = "testgroup1,testgroup2"

    return request_headers


@main.route("/")
def index():
    config = get_config()
    conf = config.get_app_config(get_request_headers(config))

    return render_template("index.html", config=conf, folder_id="")


@main.route("/folder", defaults={"subpath": ""})
@main.route("/folder/<path:subpath>")
def route_folder(subpath):
    config = get_config()
    folder_id = subpath.strip("/")
    if (not folder_id) or (not config.get_tiles(folder_id)):
        abort(404)

    conf = config.get_app_config(get_request_headers(config))

    parent = config.folder_parents.get(folder_id)
    if parent:
        back_url = url_for("main.route_folder", subpath=f"{parent}/")
    else:
        back_url = url_for("main.index")

    return render_template("index.html", config=conf, folder_id=folder_id, back_url=back_url)


@main.route("/stream-tiles/", defaults={"subpath": ""})
@main.route("/stream-tiles/<path:subpath>")
def route_stream_tiles(subpath):
    config = get_config()
    if not config.get_tiles(subpath):
        abort(404)

    request_headers = get_request_headers(config)

    def generate():
        for index, tile in config.stream_active_tiles(subpath, request_headers):
            html = render_template("tile_fragment.html", tile=tile)
            yield f"data: {json.dumps({'id': index, 'html': html})}\n\n"

        yield f"data: {json.dumps({'done': True})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@main.route("/color")
def route_color():
    config = get_config()
    request_headers = get_request_headers(config)

    if not config.is_settings_allowed(request_headers):
        abort(403)

    conf = config.get_app_config(request_headers)
    return render_template("color.html", config=conf)
