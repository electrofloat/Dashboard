import http.server
import threading

import pytest

import dashboard.auth
from dashboard.auth import Auth, TTLCache


def test_authuser():
    auth = Auth("testuser", "")
    assert auth.match(["user:testuser", ["group:admin", "group:admin2"], "group:admin3"])
    assert not auth.match(["user:testuser1", ["group:admin", "group:admin2"], "group:admin3"])
    assert auth.match([["group:admin", "group:admin2"], "user:testuser", "group:admin3"])
    assert not auth.match([["group:admin", "group:admin2"], "user:testuser1", "group:admin3"])
    assert auth.match([["group:admin", "group:admin2"], "group:admin3", "user:testuser"])
    assert not auth.match([["group:admin", "group:admin2"], "group:admin3", "user:testuser1"])


def test_authgroup():
    auth = Auth("testuser", "admin")
    assert auth.match(["user:testuser", ["group:admin", "group:admin2"], "group:admin3"])
    assert not auth.match(["user:testuser1", ["group:admin", "group:admin2"], "group:admin3"])
    assert auth.match([["group:admin", "group:admin2"], "user:testuser", "group:admin3"])
    assert not auth.match([["group:admin", "group:admin2"], "user:testuser1", "group:admin3"])
    assert auth.match([["group:admin", "group:admin2"], "group:admin3", "user:testuser"])
    assert not auth.match([["group:admin", "group:admin2"], "group:admin3", "user:testuser1"])


def test_auth_multigroup():
    auth = Auth("testuser", "admin,admin2")
    assert auth.match(["user:testuser", ["group:admin", "group:admin2"], "group:admin3"])
    assert auth.match(["user:testuser", ["group:admin4", "group:admin5"], "group:admin3"])
    assert auth.match(["user:testuser1", ["group:admin", "group:admin2"], "group:admin3"])
    assert not auth.match(
        [
            "user:testuser1",
            ["group:admin", "group:admin2", "group:admin4"],
            "group:admin3",
        ]
    )

    assert auth.match([["group:admin", "group:admin2"], "user:testuser", "group:admin3"])
    assert auth.match([["group:admin4", "group:admin5"], "user:testuser", "group:admin3"])
    assert auth.match([["group:admin", "group:admin2"], "user:testuser1", "group:admin3"])
    assert not auth.match(
        [
            ["group:admin", "group:admin2", "group:admin4"],
            "user:testuser1",
            "group:admin3",
        ]
    )

    assert auth.match([["group:admin", "group:admin2"], "group:admin3", "user:testuser"])
    assert auth.match([["group:admin4", "group:admin5"], "group:admin3", "user:testuser"])
    assert auth.match([["group:admin", "group:admin2"], "group:admin3", "user:testuser1"])
    assert not auth.match(
        [
            ["group:admin", "group:admin2", "group:admin4"],
            "group:admin3",
            "user:testuser1",
        ]
    )

    assert not auth.match([["group:admin", "user:testuser1"], "group:admin3"])
    assert not auth.match([["group:admin3", "user:testuser"], "group:admin3"])
    assert auth.match([["group:admin", "user:testuser"], "group:admin3"])
    assert auth.match([["group:admin2", "user:testuser"], "group:admin"])


def test_networks1():
    auth = Auth("", "", "10.0.0.1", {"internal": ["10.0.0.0/24"]}, "", "")

    assert auth.match_network(["internal"])
    assert not auth.match_network(["external"])
    assert auth.match_network(["internal", "10.0.1.0/24"])
    assert auth.match_network(["external", "10.0.0.0/24"])
    assert auth.match_network(["external", "10.0.0.1/32"])
    assert not auth.match_network(["external", "10.0.1.0/24"])
    assert not auth.match_network(["10.0.1.0/24", "10.0.2.0/24"])


def test_networks2():
    auth = Auth("", "", "10.0.0.1", {"internal": ["10.0.0.0/24", "172.16.0.0/24"]})

    assert auth.match_network(["internal"])
    assert not auth.match_network(["external"])
    assert auth.match_network(["internal", "10.0.1.0/24"])
    assert auth.match_network(["external", "10.0.0.0/24"])
    assert auth.match_network(["external", "10.0.0.1/32"])
    assert not auth.match_network(["external", "10.0.1.0/24"])
    assert not auth.match_network(["10.0.1.0/24", "10.0.2.0/24"])


def test_networks_without_definitions():
    auth = Auth("", "", "10.0.0.1")

    assert auth.match_network(["10.0.0.0/24"])
    assert not auth.match_network(["10.0.1.0/24", "internal"])


def test_dev_fake_auth_requires_explicit_opt_in(monkeypatch):
    auth = Auth("", "", "10.0.0.1", None, "", "https://auth.example.org")

    monkeypatch.setenv("FLASK_DEBUG", "0")
    assert not auth.match_url("https://app.example.org")
    monkeypatch.setenv("DASHBOARD_DEV_FAKE_AUTH", "0")
    assert not auth.match_url("https://app.example.org")
    monkeypatch.setenv("DASHBOARD_DEV_FAKE_AUTH", "1")
    assert auth.match_url("https://app.example.org")


@pytest.fixture
def authelia():
    requests_seen = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_HEAD(self):
            requests_seen.append(dict(self.headers))
            self.send_response(200 if "allowed" in self.headers["X-Original-URL"] else 403)
            self.send_header("Set-Cookie", "leak=1; Path=/")
            self.end_headers()

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", requests_seen
    server.shutdown()


def test_match_url(authelia):
    url, requests_seen = authelia
    auth = Auth("", "", "10.0.0.1", None, "cookie1", url, cookie_name="custom_session")

    assert auth.match_url("https://allowed.example.org")
    assert not auth.match_url("https://denied.example.org")

    assert requests_seen[0]["Cookie"] == "custom_session=cookie1"
    assert requests_seen[0]["X-Forwarded-For"] == "10.0.0.1"
    # Cookies set by Authelia must not be remembered by the shared session
    assert "leak" not in requests_seen[1]["Cookie"]
    assert len(dashboard.auth._session.cookies) == 0


def test_match_url_cache(authelia):
    url, requests_seen = authelia
    cache = TTLCache(60)
    auth1 = Auth("", "", "10.0.0.1", None, "cookie1", url, cache=cache)
    auth2 = Auth("", "", "10.0.0.1", None, "cookie2", url, cache=cache)

    assert auth1.match_url("https://allowed.example.org")
    assert auth1.match_url("https://allowed.example.org")
    assert len(requests_seen) == 1
    # Another session is never answered from the cache of the first one
    assert auth2.match_url("https://allowed.example.org")
    assert len(requests_seen) == 2

    assert TTLCache(0).get("x") is None
    disabled = TTLCache(0)
    disabled.set("x", True)
    assert disabled.get("x") is None
