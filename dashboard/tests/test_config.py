from flask import url_for

import os
from dashboard.config import Config

def url_for(param, filename):
  return param + '-' + filename

def test_norequest_headers(mocker):
  config = Config("", "")
  config.yaml_config = {
'app_config': {
  'settings':['user:testuser']
},
'tiles':
  [{'title': 'Testtitle',
    'description': 'Testdescription',
    'icon': 'testicon.png',
    'background': '#123456',
    'url': 'https://testurl.com',
    'deny': ['user:testuser']
   }
  ]
}
  request_headers = {}

  url_for_mock = mocker.patch("dashboard.config.url_for", url_for)

  assert not config.is_settings_allowed(request_headers)

  assert len(config.get_template_config(request_headers)["tiles"]) == 0

def test_noappconfig(mocker):
  config = Config("", "")
  config.yaml_config = {
'app_config': None,
'tiles':
  [{'title': 'Testtitle',
    'description': 'Testdescription',
    'icon': 'testicon.png',
    'background': '#123456',
    'url': 'https://testurl.com',
    'deny': ['user:testuser']
   }
  ]
}
  request_headers = {}
  request_headers["x_forwarded_for"] = "10.0.0.1"
  request_headers["remote_user"] = "testuser"
  request_headers["remote_groups"] = ""
  request_headers["authelia_session"] = ""

  url_for_mock = mocker.patch("dashboard.config.url_for", url_for)

  assert config.get_background_img() == "static-background.jpg"

  assert not config.is_settings_allowed(request_headers)

def test_config_common(mocker):
  config = Config("", "")
  config.yaml_config = {
'app_config':
  {'authelia_url': 'https://auth.example.org',
   'background': 'background.jpg',
   'settings': ['user:testuser']},
   'network': {'internal': ['10.0.0.0/24']
  },
'tiles':
  [{'title': 'Testtitle',
    'description': 'Testdescription',
    'icon': 'testicon.png',
    'background': '#123456',
    'url': 'https://testurl.com',
    'deny': ['user:testuser']
   }
  ]
}
  request_headers = {}
  request_headers["x_forwarded_for"] = "10.0.0.1"
  request_headers["remote_user"] = "testuser"
  request_headers["remote_groups"] = ""
  request_headers["authelia_session"] = ""

  url_for_mock = mocker.patch("dashboard.config.url_for", url_for)
  assert config.get_icon("icon.jpg") == "userdata.static-icons/icon.jpg"
  assert config.get_icon("di-icon") == "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/icon.png"
  assert config.get_icon("") == ""
  assert config.get_icon(None) == ""

  assert config.get_background_img() == "userdata.static-backgrounds/background.jpg"
  config.yaml_config["app_config"]["background"] = "https://example.org/background.jpg"
  assert config.get_background_img() == "https://example.org/background.jpg"

  config.yaml_config["app_config"]["background"] = "http://example.org/background.jpg"
  assert config.get_background_img() == "http://example.org/background.jpg"

  config.yaml_config["app_config"]["background"] = "htp://example.org/background.jpg"
  assert config.get_background_img() == "userdata.static-backgrounds/htp://example.org/background.jpg"
  config.yaml_config["app_config"]["background"] = ""
  assert config.get_background_img() == "static-background.jpg"
  config.yaml_config["app_config"].pop("background", None)
  assert config.get_background_img() == "static-background.jpg"

  assert config.is_settings_allowed(request_headers)
  request_headers["remote_user"] = "testuser1"
  assert not config.is_settings_allowed(request_headers)

def test_config_deny(mocker):
  config = Config("", "")
  config.yaml_config = {
'app_config':
  {'authelia_url': 'https://auth.example.org',
   'background': 'background.jpg',
   'settings': ['user:testuser']},
   'network': {'internal': ['10.0.0.0/24']
  },
'tiles':
  [{'title': 'Testtitle',
    'description': 'Testdescription',
    'icon': 'testicon.png',
    'background': '#123456',
    'url': 'https://testurl.com',
    'deny': ['user:testuser']
   }
  ]
}
  request_headers = {}
  request_headers["x_forwarded_for"] = "10.0.0.1"
  request_headers["remote_user"] = "testuser"
  request_headers["remote_groups"] = ""
  request_headers["authelia_session"] = ""

  url_for_mock = mocker.patch("dashboard.config.url_for", url_for)
  match_url_mock = mocker.patch("dashboard.auth.Auth.match_url", return_value = True)

  assert len(config.get_template_config(request_headers)["tiles"]) == 0

  request_headers["remote_user"] = "testuser1"
  assert len(config.get_template_config(request_headers)["tiles"]) == 1

  mocker.stop(match_url_mock)
  assert len(config.get_template_config(request_headers)["tiles"]) == 0

def test_config_deny_from_network(mocker):
  config = Config("", "")
  config.yaml_config = {
'app_config':
  {'authelia_url': 'https://auth.example.org',
   'background': 'background.jpg',
   'settings': ['user:testuser']},
   'network': {'internal': ['10.0.0.0/24']
  },
'tiles':
  [{'title': 'Testtitle',
    'description': 'Testdescription',
    'icon': 'testicon.png',
    'background': '#123456',
    'url': 'https://testurl.com',
    'deny': ['user:testuser'],
    'networks' : ['internal']
   }
  ]
}
  request_headers = {}
  request_headers["x_forwarded_for"] = "10.0.0.1"
  request_headers["remote_user"] = "testuser"
  request_headers["remote_groups"] = ""
  request_headers["authelia_session"] = ""

  url_for_mock = mocker.patch("dashboard.config.url_for", url_for)
  match_url_mock = mocker.patch("dashboard.auth.Auth.match_url", return_value = True)

  assert len(config.get_template_config(request_headers)["tiles"]) == 0

  request_headers["remote_user"] = "testuser1"
  assert len(config.get_template_config(request_headers)["tiles"]) == 1

  request_headers["remote_user"] = "testuser"
  request_headers["x_forwarded_for"] = "10.0.1.0"
  assert len(config.get_template_config(request_headers)["tiles"]) == 1

  request_headers["remote_user"] = "testuser1"
  request_headers["x_forwarded_for"] = "10.0.1.0"
  assert len(config.get_template_config(request_headers)["tiles"]) == 1

def test_config_allow(mocker):
  config = Config("", "")
  config.yaml_config = {
'app_config':
  {'authelia_url': 'https://auth.example.org',
   'background': 'background.jpg',
   'settings': ['user:testuser']},
   'network': {'internal': ['10.0.0.0/24']
  },
'tiles':
  [{'title': 'Testtitle',
    'description': 'Testdescription',
    'icon': 'testicon.png',
    'background': '#123456',
    'url': 'https://testurl.com',
    'allow': ['user:testuser']
   }
  ]
}
  request_headers = {}
  request_headers["x_forwarded_for"] = "10.0.0.1"
  request_headers["remote_user"] = "testuser"
  request_headers["remote_groups"] = ""
  request_headers["authelia_session"] = ""

  url_for_mock = mocker.patch("dashboard.config.url_for", url_for)

  assert len(config.get_template_config(request_headers)["tiles"]) == 1

  request_headers["remote_user"] = "testuser1"
  assert len(config.get_template_config(request_headers)["tiles"]) == 0

def test_config_allow_from_network(mocker):
  config = Config("", "")
  config.yaml_config = {
'app_config':
  {'authelia_url': 'https://auth.example.org',
   'background': 'background.jpg',
   'settings': ['user:testuser']},
   'network': {'internal': ['10.0.0.0/24']
  },
'tiles':
  [{'title': 'Testtitle',
    'description': 'Testdescription',
    'icon': 'testicon.png',
    'background': '#123456',
    'url': 'https://testurl.com',
    'allow': ['user:testuser'],
    'networks' : ['internal']
   }
  ]
}
  request_headers = {}
  request_headers["x_forwarded_for"] = "10.0.0.1"
  request_headers["remote_user"] = "testuser"
  request_headers["remote_groups"] = ""
  request_headers["authelia_session"] = ""

  url_for_mock = mocker.patch("dashboard.config.url_for", url_for)

  assert len(config.get_template_config(request_headers)["tiles"]) == 1

  request_headers["remote_user"] = "testuser1"
  assert len(config.get_template_config(request_headers)["tiles"]) == 0

  request_headers["remote_user"] = "testuser"
  request_headers["x_forwarded_for"] = "10.0.1.0"
  assert len(config.get_template_config(request_headers)["tiles"]) == 0

  request_headers["remote_user"] = "testuser1"
  request_headers["x_forwarded_for"] = "10.0.1.0"
  assert len(config.get_template_config(request_headers)["tiles"]) == 0
