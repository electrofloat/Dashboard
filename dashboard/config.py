from flask import url_for
import yaml
import os
from cerberus import Validator
import string
import ipaddress
import re
import webcolors

from dashboard.auth import Auth

class Config:
  def __init__(self, root_dir, user_data_path):
    self.user_data_path = user_data_path
    self.root_dir = root_dir

  def validate_network(self):
    network_definitions = self.yaml_config.get("network", None)
    if network_definitions:
      for network_list in network_definitions.values():
        for network in network_list:
         try:
           ipaddress.ip_network(network)
         except ValueError as e:
           return e

    for tile in self.yaml_config["tiles"]:
      networks = tile.get("networks", None)
      if not networks:
        continue

      for network in networks:
        try:
          ip_network = ipaddress.ip_network(network)
        except ValueError as e:
          if not network_definitions:
            return e
          if network_definitions.get(network, None) == None:
            return e

    return None

  def load(self):
    try:
      with open(os.path.join(self.user_data_path, "config.yml"), 'r') as f:
        self.yaml_config = yaml.safe_load(f)
      with open(os.path.join(self.root_dir, "listoflists.schema"), 'r') as f:
        listoflists_schema = f.read()

      subst = {
        'listoflists' : listoflists_schema
      }

      with open(os.path.join(self.root_dir, "config.schema"), 'r') as f:
        tmp_src = string.Template(f.read())
        result = tmp_src.substitute(subst)
    except Exception as error:
      return error

    schema = yaml.safe_load(result)
    v = Validator(schema)
    if not v.validate(self.yaml_config, schema):
      return yaml.dump(v.errors, default_flow_style = False)

    networks_invalid = self.validate_network()
    if networks_invalid:
      return networks_invalid

    return None

  def get_background_img(self):
    background = None

    app_config = self.yaml_config.get("app_config", None)
    if app_config:
      background = app_config.get("background", None)

    if not background:
      return url_for('static', filename="background.jpg")
    if re.search("^http(s)?://", background):
      return background

    return url_for('userdata.static', filename=f"backgrounds/{background}")

  def get_icon(self, icon):
    if not icon:
      return ""

    if icon[:2] == "di":
      return "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/{}.png".format(icon[3:])

    return url_for('userdata.static', filename=f"icons/{icon}")

  def get_foreground_color(self, color):
    color_rgb = webcolors.hex_to_rgb(color)
    luminance = 0.2126*(color_rgb.red/255.0)**2.2 + 0.7152*(color_rgb.green/255.0)**2.2 + 0.0722*(color_rgb.blue/255.0)**2.2
    luma = (0.212 * color_rgb.red + 0.701 * color_rgb.green + 0.087 * color_rgb.blue) / 255

    if luma > 0.5:
      return "black"
    else:
      return "white"

  def is_settings_allowed(self, request_headers):
    app_config = self.yaml_config.get("app_config", None)
    if not app_config:
      return False

    settings = app_config.get("settings", None)
    if not settings:
      return False

    auth = Auth(request_headers.get("remote_user", None), request_headers.get("remote_groups", None))
    return auth.match(settings)

  def get_template_config(self, request_headers):
    tiles = []
    DEFAULT_BACKGROUND="#161b1f"
    dict_appconfig = {}
    dict_tiles = {}

    if ("tiles" not in self.yaml_config) or ("app_config" not in self.yaml_config):
        return config

    authelia_url = None
    app_config = self.yaml_config.get("app_config", None)
    if app_config:
      authelia_url = app_config.get("authelia_url", None)

    dict_appconfig["background_img"] = self.get_background_img()
    auth = Auth(request_headers.get("remote_user", None), request_headers.get("remote_groups", None), request_headers.get("x_forwarded_for", None), self.yaml_config.get("network", None), request_headers.get("authelia_session", None), authelia_url)
    dict_appconfig["show_settings"] = self.is_settings_allowed(request_headers)
    for tile in self.yaml_config["tiles"]:
      dict_tiles = {}
      if ("title" not in tile) or ("url" not in tile):
          continue

      if auth.match(tile.get("deny", None)) and (auth.match_network(tile["networks"]) if "networks" in tile else True):
        continue

      skip_authelia = False
      if "allow" in tile:
        if not auth.match(tile.get("allow", None)):
          continue
        if not auth.match_network(tile.get("networks", None)):
          continue
        skip_authelia = True

      dict_tiles["url"] = tile.get("url", None)
      if (not skip_authelia) and ((not authelia_url) or (not auth.match_url(dict_tiles["url"]))):
        continue
      dict_tiles["title"] = tile["title"]
      dict_tiles["description"] = tile.get("description", "")
      dict_tiles["icon"] = self.get_icon(tile.get("icon", None))
      dict_tiles["background_color"] = tile.get("background", DEFAULT_BACKGROUND)
      dict_tiles["foreground_color"] = self.get_foreground_color(dict_tiles["background_color"])

      tiles.append(dict_tiles)

    config = ({"appconfig" : dict_appconfig, "tiles" : tiles})

    return config
