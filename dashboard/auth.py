import hashlib
import http.cookiejar
import ipaddress
import os
import threading
import time

import requests

DEFAULT_COOKIE_NAME = "authelia_session"


def dev_fake_auth():
    return os.environ.get("DASHBOARD_DEV_FAKE_AUTH") == "1"


def _create_session():
    session = requests.Session()
    session.cookies.set_policy(http.cookiejar.DefaultCookiePolicy(allowed_domains=[]))
    return session


_session = _create_session()


class AutheliaError(Exception):
    pass


class AutheliaBackoff(AutheliaError):
    pass


class Backoff:
    # Remembers a recent Authelia failure, so the following checks don't each wait for the timeout
    def __init__(self, duration):
        self.duration = duration
        self._until = 0.0

    def active(self):
        return time.monotonic() < self._until

    def trigger(self):
        self._until = time.monotonic() + self.duration


class TTLCache:
    def __init__(self, ttl, maxsize=4096):
        self.ttl = ttl
        self.maxsize = maxsize
        self._data = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            value, expires = entry
            if expires < time.monotonic():
                del self._data[key]
                return None
            return value

    def set(self, key, value):
        if self.ttl <= 0:
            return
        with self._lock:
            if len(self._data) >= self.maxsize:
                now = time.monotonic()
                self._data = {k: v for k, v in self._data.items() if v[1] >= now}
                if len(self._data) >= self.maxsize:
                    self._data.clear()
            self._data[key] = (value, time.monotonic() + self.ttl)


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
        cookie_name=DEFAULT_COOKIE_NAME,
        cache=None,
        backoff=None,
    ):
        self.user = user
        self.groups = groups
        self.ip = ip
        self.network_definitions = network_definitions or {}
        self.session_cookie = session_cookie
        self.authelia_url = authelia_url
        self.authelia_timeout = authelia_timeout
        self.cookie_name = cookie_name
        self.cache = cache
        self.backoff = backoff

    def match_url(self, url):
        if dev_fake_auth():
            return True

        if (not self.session_cookie) or (not self.ip) or (not self.authelia_url):
            return False

        cache_key = None
        if self.cache is not None:
            cookie_digest = hashlib.sha256(self.session_cookie.encode()).hexdigest()
            cache_key = (cookie_digest, self.ip, url)
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        if self.backoff is not None and self.backoff.active():
            raise AutheliaBackoff("Authelia failed recently, check skipped")

        try:
            response = _session.head(
                url=f"{self.authelia_url}/api/authz/auth-request",
                headers={
                    "Cookie": f"{self.cookie_name}={self.session_cookie}",
                    "X-Original-Method": "HEAD",
                    "X-Original-URL": url,
                    "X-Forwarded-For": self.ip,
                },
                timeout=self.authelia_timeout,
            )
        except requests.RequestException:
            if self.backoff is not None:
                self.backoff.trigger()
            raise

        # A server error is not an answer, so it must not be cached as a denial
        if response.status_code >= 500:
            if self.backoff is not None:
                self.backoff.trigger()
            raise AutheliaError(f"Authelia answered with status {response.status_code}")

        allowed = response.status_code == 200

        if cache_key is not None:
            self.cache.set(cache_key, allowed)

        return allowed

    def match_network(self, networks):
        if not networks:
            return True

        try:
            ip = ipaddress.ip_address(self.ip)
        except ValueError:
            return False

        for network in networks:
            if network in self.network_definitions:
                for network_definition in self.network_definitions[network]:
                    try:
                        ip_net = ipaddress.ip_network(network_definition)
                    except ValueError:
                        return False
                    if ip in ip_net:
                        return True
            else:
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
                if all(self.check_authorization(user_group) for user_group in outer_list_item):
                    return True
            elif self.check_authorization(outer_list_item):
                return True

        return False

    def check_authorization(self, user_or_group):
        if user_or_group.startswith("user:"):
            return self.is_user_authorized(user_or_group[5:])
        if user_or_group.startswith("group:"):
            return self.is_group_authorized(user_or_group[6:])

        return False

    def is_user_authorized(self, user):
        return user == self.user

    def is_group_authorized(self, group):
        if not self.groups:
            return False
        return any(group == remote_group.strip() for remote_group in self.groups.split(","))
