from dashboard.config import ROOT_DIR, CommonTile, Config


def match_url_test_hosts(url):
    return not any(x in url for x in ["test1", "test2", "test3"])


def assert_folder(config, subpath, request_headers, assert_count, folder_assert_count):
    def callback(index, tile):
        return (index, tile)

    folder = None
    i = -1
    for i, result in enumerate(config.stream_active_tiles(subpath, request_headers, callback)):
        index, tile = result
        if tile.title == "foldertitle":
            folder = tile.get_url_digest(index)

    assert i == (assert_count - 1)
    if not folder:
        return
    assert len(list(config.stream_active_tiles(folder, request_headers, None))) == folder_assert_count


def test_norequest_headers(mocker):
    config = Config(ROOT_DIR, "")
    yaml_config = {
        "app_config": {"settings": ["user:testuser"]},
        "tiles": [
            {
                "type": "tile",
                "title": "Testtitle",
                "description": "Testdescription",
                "icon": "testicon.png",
                "background": "#123456",
                "url": "https://testurl.com",
                "deny": ["user:testuser"],
            }
        ],
    }
    error = config.load(yaml_config)
    assert not error
    request_headers = {}

    assert not config.is_settings_allowed(request_headers)

    assert len(list(config.stream_active_tiles("/", request_headers, None))) == 0


def test_noappconfig(mocker):
    config = Config(ROOT_DIR, "")
    yaml_config = {
        "tiles": [
            {
                "type": "tile",
                "title": "Testtitle",
                "description": "Testdescription",
                "icon": "testicon.png",
                "background": "#123456",
                "url": "https://testurl.com",
                "deny": ["user:testuser"],
            }
        ]
    }
    error = config.load(yaml_config)
    assert not error

    request_headers = {}
    request_headers["x_forwarded_for"] = "10.0.0.1"
    request_headers["remote_user"] = "testuser"
    request_headers["remote_groups"] = ""
    request_headers["authelia_session"] = ""

    assert config.get_background_img() == Config.STATIC_URL + "background.jpg"

    assert not config.is_settings_allowed(request_headers)


def test_config_common(mocker):
    config = Config(ROOT_DIR, "")
    yaml_config = {
        "app_config": {
            "authelia_url": "https://auth.example.org",
            "background": "background.jpg",
            "settings": ["user:testuser"],
        },
        "network": {"internal": ["10.0.0.0/24"]},
        "tiles": [
            {
                "type": "tile",
                "title": "Testtitle",
                "description": "Testdescription",
                "icon": "testicon.png",
                "background": "#123456",
                "url": "https://testurl.com",
                "deny": ["user:testuser"],
            }
        ],
    }
    error = config.load(yaml_config)
    assert not error

    request_headers = {}
    request_headers["x_forwarded_for"] = "10.0.0.1"
    request_headers["remote_user"] = "testuser"
    request_headers["remote_groups"] = ""
    request_headers["authelia_session"] = ""

    common_tile = CommonTile({}, "")
    assert common_tile.get_icon("icon.jpg") == Config.USERDATA_URL + "icons/icon.jpg"
    assert common_tile.get_icon("di-icon") == "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/icon.png"
    assert common_tile.get_icon("") == ""
    assert common_tile.get_icon(None) == ""

    assert config.get_background_img() == Config.USERDATA_URL + "backgrounds/background.jpg"
    config.yaml_config["app_config"]["background"] = "https://example.org/background.jpg"
    assert config.get_background_img() == "https://example.org/background.jpg"

    config.yaml_config["app_config"]["background"] = "http://example.org/background.jpg"
    assert config.get_background_img() == "http://example.org/background.jpg"

    config.yaml_config["app_config"]["background"] = "htp://example.org/background.jpg"
    assert config.get_background_img() == Config.USERDATA_URL + "backgrounds/htp://example.org/background.jpg"
    config.yaml_config["app_config"]["background"] = ""
    assert config.get_background_img() == Config.STATIC_URL + "background.jpg"
    config.yaml_config["app_config"].pop("background", None)
    assert config.get_background_img() == Config.STATIC_URL + "background.jpg"

    assert config.is_settings_allowed(request_headers)
    request_headers["remote_user"] = "testuser1"
    assert not config.is_settings_allowed(request_headers)


def test_config_deny(mocker):
    config = Config(ROOT_DIR, "")
    yaml_config = {
        "app_config": {
            "authelia_url": "https://auth.example.org",
            "background": "background.jpg",
            "settings": ["user:testuser"],
        },
        "network": {"internal": ["10.0.0.0/24"]},
        "tiles": [
            {
                "type": "tile",
                "title": "Testtitle",
                "description": "Testdescription",
                "icon": "testicon.png",
                "background": "#123456",
                "url": "https://testurl.com",
                "deny": ["user:testuser"],
            },
            {
                "type": "folder",
                "title": "foldertitle",
                "tiles": [
                    {"type": "tile", "title": "testtitle2", "url": "https://test1url.com", "deny": ["user:testuser"]},
                    {"type": "tile", "title": "testtitle2", "url": "https://test2url.com", "deny": ["user:testuser"]},
                    {"type": "tile", "title": "testtitle3", "url": "https://test4url.com", "deny": ["user:testuser1"]},
                ],
            },
        ],
    }

    error = config.load(yaml_config)
    assert not error

    request_headers = {}
    request_headers["x_forwarded_for"] = "10.0.0.1"
    request_headers["remote_user"] = "testuser"
    request_headers["remote_groups"] = ""
    request_headers["authelia_session"] = ""

    match_url_mock = mocker.patch("dashboard.auth.Auth.match_url", return_value=True)

    assert len(list(config.stream_active_tiles("/", request_headers, None))) == 1

    request_headers["remote_user"] = "testuser1"

    assert_folder(config, "/", request_headers, 2, 2)

    mocker.stop(match_url_mock)
    mocker.patch("dashboard.auth.Auth.match_url", side_effect=match_url_test_hosts)
    assert len(list(config.stream_active_tiles("/", request_headers, None))) == 1

    request_headers["remote_user"] = "testuser2"
    assert_folder(config, "/", request_headers, 2, 1)


def test_config_deny_from_network(mocker):
    config = Config(ROOT_DIR, "")
    yaml_config = {
        "app_config": {
            "authelia_url": "https://auth.example.org",
            "background": "background.jpg",
            "settings": ["user:testuser"],
        },
        "network": {"internal": ["10.0.0.0/24"]},
        "tiles": [
            {
                "type": "tile",
                "title": "Testtitle",
                "description": "Testdescription",
                "icon": "testicon.png",
                "background": "#123456",
                "url": "https://testurl.com",
                "deny": ["user:testuser"],
                "networks": ["internal"],
            },
            {
                "type": "folder",
                "title": "foldertitle",
                "tiles": [
                    {
                        "type": "tile",
                        "title": "testtitle2",
                        "url": "https://test1url.com",
                        "deny": ["user:testuser"],
                        "networks": ["internal"],
                    },
                    {
                        "type": "tile",
                        "title": "testtitle2",
                        "url": "https://test2url.com",
                        "deny": ["user:testuser"],
                        "networks": ["internal"],
                    },
                    {"type": "tile", "title": "testtitle3", "url": "https://test4url.com", "deny": ["user:testuser1"]},
                ],
            },
        ],
    }
    error = config.load(yaml_config)
    assert not error

    request_headers = {}
    request_headers["x_forwarded_for"] = "10.0.0.1"
    request_headers["remote_user"] = "testuser"
    request_headers["remote_groups"] = ""
    request_headers["authelia_session"] = ""

    mocker.patch("dashboard.auth.Auth.match_url", return_value=True)

    assert_folder(config, "/", request_headers, 1, 1)

    request_headers["remote_user"] = "testuser1"
    assert_folder(config, "/", request_headers, 2, 2)

    request_headers["remote_user"] = "testuser"
    request_headers["x_forwarded_for"] = "10.0.1.0"
    assert_folder(config, "/", request_headers, 2, 3)

    request_headers["remote_user"] = "testuser1"
    request_headers["x_forwarded_for"] = "10.0.1.0"
    assert_folder(config, "/", request_headers, 2, 2)


def test_config_allow(mocker):
    config = Config(ROOT_DIR, "")
    yaml_config = {
        "app_config": {
            "authelia_url": "https://auth.example.org",
            "background": "background.jpg",
            "settings": ["user:testuser"],
        },
        "network": {"internal": ["10.0.0.0/24"]},
        "tiles": [
            {
                "type": "tile",
                "title": "Testtitle",
                "description": "Testdescription",
                "icon": "testicon.png",
                "background": "#123456",
                "url": "https://testurl.com",
                "allow": ["user:testuser"],
            },
            {
                "type": "folder",
                "title": "foldertitle",
                "tiles": [
                    {
                        "type": "tile",
                        "title": "testtitle2",
                        "url": "https://test1url.com",
                        "allow": ["user:testuser"],
                    },
                    {
                        "type": "tile",
                        "title": "testtitle2",
                        "url": "https://test2url.com",
                        "allow": ["user:testuser"],
                    },
                    {"type": "tile", "title": "testtitle3", "url": "https://test4url.com", "allow": ["user:testuser1"]},
                ],
            },
        ],
    }
    error = config.load(yaml_config)
    assert not error

    request_headers = {}
    request_headers["x_forwarded_for"] = "10.0.0.1"
    request_headers["remote_user"] = "testuser"
    request_headers["remote_groups"] = ""
    request_headers["authelia_session"] = ""

    assert_folder(config, "/", request_headers, 2, 2)

    request_headers["remote_user"] = "testuser1"
    assert_folder(config, "/", request_headers, 1, 1)


def test_config_allow_from_network(mocker):
    config = Config(ROOT_DIR, "")
    yaml_config = {
        "app_config": {
            "authelia_url": "https://auth.example.org",
            "background": "background.jpg",
            "settings": ["user:testuser"],
        },
        "network": {"internal": ["10.0.0.0/24"]},
        "tiles": [
            {
                "type": "tile",
                "title": "Testtitle",
                "description": "Testdescription",
                "icon": "testicon.png",
                "background": "#123456",
                "url": "https://testurl.com",
                "allow": ["user:testuser"],
                "networks": ["internal"],
            },
            {
                "type": "folder",
                "title": "foldertitle",
                "tiles": [
                    {
                        "type": "tile",
                        "title": "testtitle2",
                        "url": "https://test1url.com",
                        "allow": ["user:testuser"],
                        "networks": ["internal"],
                    },
                    {
                        "type": "tile",
                        "title": "testtitle2",
                        "url": "https://test2url.com",
                        "allow": ["user:testuser"],
                        "networks": ["internal"],
                    },
                    {"type": "tile", "title": "testtitle3", "url": "https://test4url.com", "allow": ["user:testuser1"]},
                ],
            },
        ],
    }
    error = config.load(yaml_config)
    assert not error

    request_headers = {}
    request_headers["x_forwarded_for"] = "10.0.0.1"
    request_headers["remote_user"] = "testuser"
    request_headers["remote_groups"] = ""
    request_headers["authelia_session"] = ""

    assert_folder(config, "/", request_headers, 2, 2)

    request_headers["remote_user"] = "testuser1"
    assert_folder(config, "/", request_headers, 1, 1)

    request_headers["remote_user"] = "testuser"
    request_headers["x_forwarded_for"] = "10.0.1.0"
    assert_folder(config, "/", request_headers, 0, 0)

    request_headers["remote_user"] = "testuser1"
    request_headers["x_forwarded_for"] = "10.0.1.0"
    assert_folder(config, "/", request_headers, 1, 1)


def test_client_ip():
    config = Config(ROOT_DIR, "")
    assert not config.load(
        {
            "app_config": {"trusted_proxies": ["172.16.0.0/12"]},
            "tiles": [{"type": "tile", "title": "t", "url": "https://t.com"}],
        }
    )

    assert config.get_client_ip("172.16.0.2", None) == "172.16.0.2"
    assert config.get_client_ip("172.16.0.2", "10.0.0.1") == "10.0.0.1"
    assert config.get_client_ip("172.16.0.2", "1.2.3.4, 10.0.0.1") == "10.0.0.1"
    assert config.get_client_ip("172.16.0.2", "1.2.3.4, 10.0.0.1, 172.16.0.3") == "10.0.0.1"
    assert config.is_peer_trusted("172.16.0.2")
    assert not config.is_peer_trusted("10.0.0.1")


def test_invalid_trusted_proxy():
    config = Config(ROOT_DIR, "")
    assert config.load(
        {
            "app_config": {"trusted_proxies": ["not-a-network"]},
            "tiles": [{"type": "tile", "title": "t", "url": "https://t.com"}],
        }
    )
