import copy

import pytest
from fastapi.testclient import TestClient

from app.api import audit_controller
from app.preferences import store
from app.preferences.store import Preferences
from app.server import app
from kan102_support import SECRET, SECRET_ENV


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch):
    monkeypatch.setenv(SECRET_ENV, SECRET)


@pytest.fixture(autouse=True)
def seeded_store(monkeypatch):
    """Isolated, seeded in-memory store (nothing in the app writes to it, so tests must seed)."""
    data = {
        "cust-1": Preferences(email=True, sms=False, push_notification=True),
        "cust-2": Preferences(email=False, sms=True, push_notification=False),
        "allfalse": Preferences(email=False, sms=False, push_notification=False),
        "alltrue": Preferences(email=True, sms=True, push_notification=True),
        "A": Preferences(email=True, sms=False, push_notification=False),
        "a": Preferences(email=False, sms=False, push_notification=True),
    }
    monkeypatch.setattr(store, "PREFERENCE_STORE", data)
    return data


@pytest.fixture
def snapshot(seeded_store):
    """Callable returning a deep copy of the store for before/after comparisons."""
    return lambda: copy.deepcopy(seeded_store)


@pytest.fixture
def client():
    # raise_server_exceptions=False so an unhandled app error surfaces as a 500 response we can assert on
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def lookup_spy(monkeypatch):
    """Records every store lookup made by the controller, to prove 'no processing occurs' on rejection."""
    calls = []
    real = audit_controller.lookup

    def spy(customer_id):
        calls.append(customer_id)
        return real(customer_id)

    monkeypatch.setattr(audit_controller, "lookup", spy)
    return calls
