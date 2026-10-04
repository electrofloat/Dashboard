import hashlib
import html
import json
import os
import re

import pytest

from dashboard import create_app

CONFIG = """
app_config:
  trusted_proxies: ['172.16.0.0/12']
  settings: ['user:testuser']
tiles:
  - type: tile
    title: 'Backslash C:\\temp \\u003cimg src=x onerror=alert(1)\\u003e "quoted"'
    description: "line1\\nline2"
    url: https://one.example.org
    allow: ['user:testuser']
  - type: folder
    title: Folder
    tiles:
      - type: tile
        title: Inner
        url: https://inner.example.org
        allow: ['user:testuser']
"""

PROXY = {"REMOTE_ADDR": "172.16.0.2"}
USER = {"Remote-User": "testuser"}


def make_client(tmp_path, config=CONFIG):
    (tmp_path / "config.yml").write_text(config)
    return create_app(str(tmp_path)).test_client()


def read_events(response):
    events = []
    for line in response.get_data(as_text=True).split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: ") :]))
    return events


def test_stream_is_valid_json(tmp_path):
    client = make_client(tmp_path)
    events = read_events(client.get("/stream-tiles/", headers=USER, environ_base=PROXY))

    assert events[-1] == {"done": True}
    tiles = [event for event in events if "html" in event]
    assert len(tiles) == 2

    html = next(event["html"] for event in tiles if event["id"] == 0)
    assert "C:\\temp" in html
    assert "\\u003cimg" in html
    assert "<img src=x" not in html
    assert "&#34;quoted&#34;" in html


def test_folder_deep_link_after_start(tmp_path):
    client = make_client(tmp_path)
    app = client.application
    digest = next(iter(app.extensions["dashboard.config"].config.id_hash))

    assert client.get(f"/folder/{digest}/", headers=USER, environ_base=PROXY).status_code == 200
    events = read_events(client.get(f"/stream-tiles/{digest}/", headers=USER, environ_base=PROXY))
    assert len(events) == 2

    assert client.get("/folder/unknown/").status_code == 404
    assert client.get("/stream-tiles/unknown/").status_code == 404
    assert client.get(f"/folder/{digest}/extra'text").status_code == 404


def test_back_button(tmp_path):
    client = make_client(
        tmp_path,
        """
app_config:
  trusted_proxies: ['172.16.0.0/12']
tiles:
  - type: folder
    id: outer
    title: Outer
    tiles:
      - type: folder
        id: inner
        title: Inner
        tiles:
          - {type: tile, title: T, url: 'https://t.example.org', allow: ['user:testuser']}
""",
    )

    assert 'aria-label="Back"' not in client.get("/", headers=USER, environ_base=PROXY).get_data(as_text=True)
    assert 'href="/" aria-label="Back"' in client.get("/folder/outer/", headers=USER, environ_base=PROXY).get_data(as_text=True)
    assert 'href="/folder/outer/" aria-label="Back"' in client.get("/folder/inner/", headers=USER, environ_base=PROXY).get_data(as_text=True)


def test_tile_label_naming(tmp_path):
    client = make_client(tmp_path)
    events = read_events(client.get("/stream-tiles/", headers=USER, environ_base=PROXY))
    folder = next(event["html"] for event in events if event.get("id") == 1)

    assert 'aria-label="Folder"' in folder
    assert "<img" not in folder
    assert 'role="img"' not in folder


def test_untrusted_peer_headers_ignored(tmp_path):
    client = make_client(tmp_path)

    events = read_events(client.get("/stream-tiles/", headers=USER, environ_base={"REMOTE_ADDR": "10.0.0.5"}))
    assert events == [{"done": True}]
    assert client.get("/color", headers=USER, environ_base={"REMOTE_ADDR": "10.0.0.5"}).status_code == 403
    assert client.get("/color", headers=USER, environ_base=PROXY).status_code == 200


@pytest.mark.parametrize("value", ["0", "1", ""])
def test_flask_debug_does_not_fake_auth(tmp_path, monkeypatch, value):
    monkeypatch.setenv("FLASK_DEBUG", value)
    client = make_client(tmp_path)

    events = read_events(client.get("/stream-tiles/", environ_base=PROXY))
    assert events == [{"done": True}]


def test_dev_fake_auth(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DEV_FAKE_AUTH", "1")
    client = make_client(tmp_path)

    events = read_events(client.get("/stream-tiles/", environ_base={"REMOTE_ADDR": "10.0.0.5"}))
    assert len(events) == 3


def test_config_error_not_disclosed(tmp_path):
    client = make_client(tmp_path, "tiles: []\nsecret_key: verysecretkey\n")

    for url in ["/", "/stream-tiles/", "/color", "/folder/x/"]:
        response = client.get(url)
        assert response.status_code == 500
        assert "verysecretkey" not in response.get_data(as_text=True)


def test_security_headers(tmp_path):
    client = make_client(tmp_path)
    response = client.get("/", headers=USER, environ_base=PROXY)

    assert response.status_code == 200
    assert "script-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "<script>" not in response.get_data(as_text=True)


def test_healthz(tmp_path):
    assert make_client(tmp_path).get("/healthz").status_code == 200
    assert make_client(tmp_path, "tiles: []\n").get("/healthz").status_code == 500


def test_no_icon_cdn(tmp_path):
    client = make_client(tmp_path)
    response = client.get("/", headers=USER, environ_base=PROXY)

    assert "bootstrap-icons" not in response.get_data(as_text=True)
    assert "<svg" in response.get_data(as_text=True)
    assert "cdn.jsdelivr.net" not in response.headers["Content-Security-Policy"]


def test_background_url_escaped(tmp_path):
    client = make_client(tmp_path, CONFIG.replace("app_config:", 'app_config:\n  background: "x\');background:red;/*"'))
    page = client.get("/", headers=USER, environ_base=PROXY).get_data(as_text=True)

    start = page.index('<div class="hero-body" style="') + len('<div class="hero-body" style="')
    style = html.unescape(page[start : page.index('"', start)])
    assert 'url("/static/userdata/backgrounds/x\\27 \\29 ;background:red;/*")' in style


def tile_config(*titles):
    tiles = "".join(f"  - {{type: tile, title: {t}, url: 'https://{t}.example.org', allow: ['user:testuser']}}\n" for t in titles)
    return f"app_config:\n  trusted_proxies: ['172.16.0.0/12']\ntiles:\n{tiles}"


def stream_titles(client):
    events = read_events(client.get("/stream-tiles/", headers=USER, environ_base=PROXY))
    return sorted(event["html"].split('class="titl ')[1].split(">")[1].split("<")[0] for event in events if "html" in event)


def test_config_reload(tmp_path):
    client = make_client(tmp_path, tile_config("first"))
    client.application.extensions["dashboard.config"].interval = 0
    assert stream_titles(client) == ["first"]

    (tmp_path / "config.yml").write_text(tile_config("first", "second"))
    assert stream_titles(client) == ["first", "second"]

    (tmp_path / "config.yml").write_text("tiles: []\n")
    assert client.get("/", headers=USER, environ_base=PROXY).status_code == 200
    assert stream_titles(client) == ["first", "second"]


def test_config_reload_recovers_from_startup_error(tmp_path):
    client = make_client(tmp_path, "tiles: []\n")
    client.application.extensions["dashboard.config"].interval = 0
    assert client.get("/").status_code == 500

    (tmp_path / "config.yml").write_text(tile_config("fixed"))
    assert stream_titles(client) == ["fixed"]


def test_config_reload_interval(tmp_path):
    client = make_client(tmp_path, tile_config("first"))
    assert stream_titles(client) == ["first"]

    (tmp_path / "config.yml").write_text(tile_config("first", "second"))
    assert stream_titles(client) == ["first"]


def test_page_title(tmp_path):
    client = make_client(tmp_path, CONFIG.replace("app_config:", "app_config:\n  title: Home Lab"))
    digest = next(iter(client.application.extensions["dashboard.config"].config.id_hash))

    assert "<title>Home Lab</title>" in client.get("/", headers=USER, environ_base=PROXY).get_data(as_text=True)
    folder_page = client.get(f"/folder/{digest}/", headers=USER, environ_base=PROXY).get_data(as_text=True)
    assert "<title>Folder - Home Lab</title>" in folder_page


def test_search_data(tmp_path):
    client = make_client(tmp_path)
    events = read_events(client.get("/stream-tiles/", headers=USER, environ_base=PROXY))
    folder = next(event["html"] for event in events if event.get("id") == 1)

    assert 'data-search="Folder "' in folder
    page = client.get("/", headers=USER, environ_base=PROXY).get_data(as_text=True)
    assert 'id="search"' in page
    assert "<title>Dashboard</title>" in page


def test_settings_page_config_snippet(tmp_path):
    page = make_client(tmp_path).get("/color", headers=USER, environ_base=PROXY).get_data(as_text=True)

    assert 'id="url_input"' in page
    assert 'id="yaml"' in page
    assert 'id="copy"' in page


def test_recursive_stream(tmp_path):
    client = make_client(tmp_path)
    events = read_events(client.get("/stream-tiles/?recursive=1", headers=USER, environ_base=PROXY))
    tiles = [event for event in events if "html" in event]

    assert events[-1] == {"done": True}
    assert len(tiles) == 1
    assert '<div class="path white">Folder</div>' in tiles[0]["html"]
    assert 'data-search="Inner "' in tiles[0]["html"]

    assert read_events(client.get("/stream-tiles/?recursive=1", environ_base=PROXY)) == [{"done": True}]


def test_subfolder_toggle_only_with_subfolders(tmp_path):
    client = make_client(tmp_path)
    digest = next(iter(client.application.extensions["dashboard.config"].config.id_hash))

    assert 'id="search-subfolders"' in client.get("/", headers=USER, environ_base=PROXY).get_data(as_text=True)
    folder_page = client.get(f"/folder/{digest}/", headers=USER, environ_base=PROXY).get_data(as_text=True)
    assert 'id="search-subfolders"' not in folder_page


def test_static_urls_are_versioned(tmp_path):
    client = make_client(tmp_path)
    page = client.get("/", headers=USER, environ_base=PROXY).get_data(as_text=True)
    url = re.search(r'src="(/static/index\.js\?v=[0-9a-f]+)"', page).group(1)

    with open(os.path.join(client.application.static_folder, "index.js"), "rb") as f:
        assert url.endswith(hashlib.sha256(f.read()).hexdigest()[:12])

    cache_control = client.get(url).headers["Cache-Control"]
    assert "max-age=31536000" in cache_control and "immutable" in cache_control
    assert "no-cache" not in cache_control
    assert "max-age" not in client.get("/static/index.js").headers["Cache-Control"]
