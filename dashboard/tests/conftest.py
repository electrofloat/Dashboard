import pytest


@pytest.fixture(autouse=True)
def no_dev_fake_auth(monkeypatch):
    monkeypatch.delenv("DASHBOARD_DEV_FAKE_AUTH", raising=False)
