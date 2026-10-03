import ipaddress
import os

import requests


class Auth:
    def __init__(
        self,
        user,
        groups,
        ip=None,
        network_definitions=None,
        session_cookie=None,
        authelia_url=None,
        authelia_timeout=5,
    ):
        self.user = user
        self.groups = groups
        self.ip = ip
        self.network_definitions = network_definitions
        self.session_cookie = session_cookie
        self.authelia_url = authelia_url
        self.authelia_timeout = authelia_timeout
        self.session = requests.Session()

    def match_url(self, url):
        if "FLASK_DEBUG" in os.environ:
            matches = ["test1", "test2", "test3"]
            if any(x in url for x in matches):
                return False
            return True

        if (not self.session_cookie) or (not self.ip) or (not self.authelia_url):
            return False

        status = self.session.head(
            url=f"{self.authelia_url}/api/authz/auth-request",
            cookies={"authelia_session": self.session_cookie},
            headers={"X-Original-Method": "HEAD", "X-Original-URL": url, "X-Forwarded-For": self.ip},
            timeout=self.authelia_timeout,
        )

        if status.status_code != 200:
            return False

        return True

    def match_network(self, networks):
        if not networks:
            return True

        ip = None
        try:
            ip = ipaddress.ip_address(self.ip)
        except ValueError:
            return False

        for network in networks:
            if network in self.network_definitions:
                for network_definition in self.network_definitions[network]:
                    ip_net = None
                    try:
                        ip_net = ipaddress.ip_network(network_definition)
                    except ValueError:
                        return False
                    if ip in ip_net:
                        return True
            else:
                ip_net = None
                try:
                    ip_net = ipaddress.ip_network(network)
                except ValueError:
                    continue
                if ip in ip_net:
                    return True

        return False

    def match(self, authorization_list):
        if not authorization_list:
            return False

        for outer_list_item in authorization_list:
            if isinstance(outer_list_item, list):
                authorized = True
                for user_group in outer_list_item:
                    authorized = authorized and self.check_authorization(user_group)
                if authorized:
                    return True
            else:
                if self.check_authorization(outer_list_item):
                    return True

        return False

    def check_authorization(self, user_or_group):
        if user_or_group[:4] == "user":
            return self.is_user_authorized(user_or_group[5:])
        if user_or_group[:5] == "group":
            return self.is_group_authorized(user_or_group[6:])

        return False

    def is_user_authorized(self, user):
        if user == self.user:
            return True

        return False

    def is_group_authorized(self, group):
        if not self.groups:
            return False
        for remote_group in self.groups.split(","):
            if group == remote_group.strip():
                return True

        return False
