from dashboard.auth import Auth


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
    assert not auth.match(["user:testuser1", ["group:admin", "group:admin2", "group:admin4"], "group:admin3"])

    assert auth.match([["group:admin", "group:admin2"], "user:testuser", "group:admin3"])
    assert auth.match([["group:admin4", "group:admin5"], "user:testuser", "group:admin3"])
    assert auth.match([["group:admin", "group:admin2"], "user:testuser1", "group:admin3"])
    assert not auth.match([["group:admin", "group:admin2", "group:admin4"], "user:testuser1", "group:admin3"])

    assert auth.match([["group:admin", "group:admin2"], "group:admin3", "user:testuser"])
    assert auth.match([["group:admin4", "group:admin5"], "group:admin3", "user:testuser"])
    assert auth.match([["group:admin", "group:admin2"], "group:admin3", "user:testuser1"])
    assert not auth.match([["group:admin", "group:admin2", "group:admin4"], "group:admin3", "user:testuser1"])

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
