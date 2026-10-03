import base64
import concurrent.futures
import hashlib
import ipaddress
import json
import logging
import os
import re

import webcolors
import yaml
from jsonschema import Draft202012Validator

from dashboard.auth import DEFAULT_COOKIE_NAME, Auth, TTLCache

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Upper bound for the parallel tile authorization checks of a single request
MAX_WORKERS = 8
# Seconds after which a tile stream gives up waiting for the remaining tiles
STREAM_TIMEOUT = 30
DEFAULT_CACHE_TTL = 30

logger = logging.getLogger(__name__)


def folder_digest(title, index, parent=""):
    id = f"{parent}/{title}{index}" if parent else f"{title}{index}"
    digest = hashlib.sha256(id.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")[:12]


class CommonTile:
    DEFAULT_BACKGROUND = "#161b1f"

    def __init__(self, tile_data, index):
        self.title = tile_data.get("title", "")
        self.description = tile_data.get("description", "")
        self.icon = self.get_icon(tile_data.get("icon", None))
        self.background_color = tile_data.get("background", self.DEFAULT_BACKGROUND)
        self.foreground_color = self.get_foreground_color(self.background_color)
        self.url = tile_data.get("url", None)
        self.index = index
        self.type = tile_data.get("type", "")

    def get_icon(self, icon):
        if not icon:
            return ""

        if icon[:2] == "di":
            return "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/{}.png".format(icon[3:])
        if re.search("^http(s)?://", icon):
            return icon

        return Config.USERDATA_URL + f"icons/{icon}"

    def get_foreground_color(self, color):
        color_rgb = webcolors.hex_to_rgb(color)
        luma = (0.212 * color_rgb.red + 0.701 * color_rgb.green + 0.087 * color_rgb.blue) / 255

        if luma > 0.5:
            return "black"
        else:
            return "white"


class Tile(CommonTile):
    pass


class Folder(CommonTile):
    def __init__(self, tile_data, index, digest):
        super().__init__(tile_data, index)
        self.digest = digest
        self.url = f"/folder/{digest}/"
        self.tiles = tile_data.get("tiles", None)


class Config:
    STATIC_URL = "/static/"
    USERDATA_URL = "/static/userdata/"

    def __init__(self, root_dir=ROOT_DIR, user_data_path=""):
        self.user_data_path = user_data_path
        self.root_dir = root_dir
        self.yaml_config = None
        self.app_config = None
        self.authelia_url = None
        self.authelia_timeout = 5
        self.authelia_cookie_name = DEFAULT_COOKIE_NAME
        self.authz_cache = TTLCache(DEFAULT_CACHE_TTL)
        self.trusted_proxies = None
        self.id_hash = {}
        self.folder_digests = {}
        self.folder_parents = {}

    def validate_network(self):
        network_definitions = self.yaml_config.get("network", None)
        if network_definitions:
            for network_list in network_definitions.values():
                for network in network_list:
                    try:
                        ipaddress.ip_network(network)
                    except ValueError as e:
                        return e

        for network in (self.yaml_config.get("app_config") or {}).get("trusted_proxies", []):
            try:
                ipaddress.ip_network(network)
            except ValueError as e:
                return e

        def validate_tiles(tiles):
            for tile in tiles:
                if tile["type"] == "folder":
                    error = validate_tiles(tile["tiles"])
                    if error:
                        return error
                    continue

                for network in tile.get("networks", None) or []:
                    try:
                        ipaddress.ip_network(network)
                    except ValueError as e:
                        if not network_definitions:
                            return e
                        if network_definitions.get(network, None) is None:
                            return e
            return None

        return validate_tiles(self.yaml_config["tiles"])

    def index_folders(self, tiles, parent=""):
        for index, tile_data in enumerate(tiles):
            if tile_data["type"] != "folder":
                continue
            digest = tile_data.get("id") or folder_digest(tile_data["title"], index, parent)
            if digest in self.id_hash:
                return f"Folder id '{digest}' of folder '{tile_data['title']}' is used more than once"
            self.id_hash[digest] = tile_data["tiles"]
            self.folder_digests[id(tile_data)] = digest
            self.folder_parents[digest] = parent
            error = self.index_folders(tile_data["tiles"], digest)
            if error:
                return error
        return None

    def load(self, from_var=None):
        try:
            if from_var:
                self.yaml_config = from_var
            else:
                with open(os.path.join(self.user_data_path, "config.yml"), "r") as f:
                    self.yaml_config = yaml.safe_load(f)
            with open(os.path.join(self.root_dir, "json.schema"), "r") as f:
                schema = json.load(f)
        except Exception as error:
            return error

        validator = Draft202012Validator(schema)
        validator_errors = sorted(validator.iter_errors(self.yaml_config), key=lambda e: list(e.path))
        if validator_errors:
            error = "\n"
            for validator_error in validator_errors:
                path = ".".join(str(p) for p in validator_error.path) or "<root>"
                error += f"* Path: {path}\n"
                error += f"  Message: {validator_error.message}\n"

                if validator_error.context:
                    error += "  Sub-errors:\n"
                    for sub in validator_error.context:
                        error += f"    - {sub.message}\n"

            return error

        networks_invalid = self.validate_network()
        if networks_invalid:
            return networks_invalid

        self.id_hash = {}
        self.folder_digests = {}
        self.folder_parents = {}
        folders_invalid = self.index_folders(self.yaml_config["tiles"])
        if folders_invalid:
            return folders_invalid

        self.app_config = self.yaml_config.get("app_config", None)
        if self.app_config:
            self.authelia_url = self.app_config.get("authelia_url", None)
            self.authelia_timeout = self.app_config.get("authelia_timeout", 5)
            self.authelia_cookie_name = self.app_config.get("authelia_cookie_name", DEFAULT_COOKIE_NAME)
            self.authz_cache = TTLCache(self.app_config.get("authelia_cache_ttl", DEFAULT_CACHE_TTL))
            trusted_proxies = self.app_config.get("trusted_proxies", None)
            if trusted_proxies:
                self.trusted_proxies = [ipaddress.ip_network(network) for network in trusted_proxies]

        return None

    def is_trusted_proxy(self, address):
        if not self.trusted_proxies or not address:
            return False
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            return False
        return any(ip in network for network in self.trusted_proxies)

    def is_peer_trusted(self, remote_addr):
        if not self.trusted_proxies:
            return True
        return self.is_trusted_proxy(remote_addr)

    def get_client_ip(self, remote_addr, forwarded_for):
        if not forwarded_for:
            return remote_addr

        hops = [hop.strip() for hop in forwarded_for.split(",") if hop.strip()]
        if not hops:
            return remote_addr

        for hop in reversed(hops):
            if not self.is_trusted_proxy(hop):
                return hop
        return hops[0]

    def get_background_img(self):
        background = None

        if self.app_config:
            background = self.app_config.get("background", None)

        if not background:
            return Config.STATIC_URL + "background.jpg"
        if re.search("^http(s)?://", background):
            return background

        return Config.USERDATA_URL + f"backgrounds/{background}"

    def is_settings_allowed(self, request_headers):
        if not self.app_config:
            return False

        settings = self.app_config.get("settings", None)
        if not settings:
            return False

        auth = Auth(
            request_headers.get("remote_user", None),
            request_headers.get("remote_groups", None),
        )
        return auth.match(settings)

    def get_app_config(self, request_headers):
        dict_appconfig = {}
        config = {"appconfig": dict_appconfig}

        dict_appconfig["background_img"] = self.get_background_img()
        dict_appconfig["show_settings"] = self.is_settings_allowed(request_headers)

        return config

    def get_tiles(self, folder_id):
        folder_id = (folder_id or "").strip("/")
        if not folder_id:
            return self.yaml_config["tiles"]

        return self.id_hash.get(folder_id, None)

    def is_tile_permitted(self, auth, tile):
        if auth.match(tile.get("deny", None)) and (
            auth.match_network(tile["networks"]) if "networks" in tile else True
        ):
            return False

        skip_authelia = False
        if "allow" in tile:
            if not auth.match(tile.get("allow", None)):
                return False
            if not auth.match_network(tile.get("networks", None)):
                return False
            skip_authelia = True

        if (not skip_authelia) and ((not self.authelia_url) or (not auth.match_url(tile.get("url", None)))):
            return False

        return True

    def is_folder_permitted(self, auth, tiles):
        for tile in tiles:
            if tile["type"] == "folder":
                if self.is_folder_permitted(auth, tile["tiles"]):
                    return True
            elif self.is_tile_permitted(auth, tile):
                return True

        return False

    def get_tile(self, auth, index, tile_data):
        if tile_data["type"] == "folder":
            if not self.is_folder_permitted(auth, tile_data["tiles"]):
                return None
            return Folder(tile_data, index, self.folder_digests[id(tile_data)])

        if not self.is_tile_permitted(auth, tile_data):
            return None
        return Tile(tile_data, index)

    def create_auth(self, request_headers):
        return Auth(
            request_headers.get("remote_user", None),
            request_headers.get("remote_groups", None),
            request_headers.get("x_forwarded_for", None),
            self.yaml_config.get("network", None),
            request_headers.get("authelia_session", None),
            self.authelia_url,
            self.authelia_timeout,
            self.authelia_cookie_name,
            self.authz_cache,
        )

    def stream_active_tiles(self, folder_id, request_headers, callback=None):
        tiles = self.get_tiles(folder_id)
        if not tiles:
            return

        auth = self.create_auth(request_headers)

        def process(index, tile_data):
            try:
                return self.get_tile(auth, index, tile_data)
            except Exception as error:
                logger.warning(
                    "Authorization check failed for tile '%s': %s",
                    tile_data.get("title"),
                    error,
                )
                return None

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(tiles)))
        try:
            futures = {executor.submit(process, i, t): i for i, t in enumerate(tiles)}
            for future in concurrent.futures.as_completed(futures, timeout=STREAM_TIMEOUT):
                tile = future.result()
                if not tile:
                    continue
                index = futures[future]
                if callback:
                    yield callback(index, tile)
                else:
                    yield (index, tile)
        except concurrent.futures.TimeoutError:
            logger.warning("Streaming tiles timed out")
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
