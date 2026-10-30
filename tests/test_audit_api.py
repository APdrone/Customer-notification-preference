"""KAN-102: bulk customer notification preferences audit API."""
import base64
import copy
import hashlib
import hmac
import json
import logging
import time

import pytest
from fastapi.testclient import TestClient

from app.api import audit_controller
from app.preferences import store
from app.preferences.store import Preferences
from app.server import app

URL = "/api/v1/customers/audit/preferences"
SECRET = "unit-test-secret-not-a-real-key"
SECRET_ENV = "JWT_SECRET_KEY"


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def make_token(claims=None, secret=SECRET, header=None, sign=True):
    header = header if header is not None else {"alg": "HS256", "typ": "JWT"}
    base = {"sub": "auditor-1", "role": "admin", "exp": int(time.time()) + 600}
    payload = base if claims is None else claims
    h = _b64(json.dumps(header).encode())
    p = _b64(json.dumps(payload).encode())
    sig = hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest() if sign else b""
    return f"{h}.{p}.{_b64(sig)}"


def auth(token=None):
    return {"Authorization": f"Bearer {token or make_token()}"}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv(SECRET_ENV, SECRET)
    original = copy.deepcopy(store.PREFERENCE_STORE)
    store.PREFERENCE_STORE.clear()
    store.PREFERENCE_STORE["cust-1"] = Preferences(email=True, sms=False, push_notification=True)
    store.PREFERENCE_STORE["cust-2"] = Preferences(email=False, sms=True, push_notification=False)
    yield
    store.PREFERENCE_STORE.clear()
    store.PREFERENCE_STORE.update(original)


@pytest.fixture
def client():
    return TestClient(app)


def assert_problem(resp, status, title):
    assert resp.status_code == status
    assert resp.headers["content-type"].startswith("application/problem+json")
    body = resp.json()
    assert set(body) == {"type", "title", "status", "detail", "instance"}
    assert body["status"] == status and body["title"] == title
    assert body["instance"] == URL
    return body


# ---- AC-1 / AC-2: success, partial matches, missing -------------------------------------------

def test_happy_path_returns_all_channels_in_request_order(client):
    r = client.post(URL, json={"customerIds": ["cust-2", "cust-1"]}, headers=auth())
    assert r.status_code == 200
    assert r.json() == {
        "results": [
            {"customerId": "cust-2", "missing": False,
             "preferences": {"email": False, "sms": True, "push_notification": False}},
            {"customerId": "cust-1", "missing": False,
             "preferences": {"email": True, "sms": False, "push_notification": True}},
        ]
    }


def test_partial_match_marks_missing_customers(client):
    r = client.post(URL, json={"customerIds": ["cust-1", "ghost", "cust-2"]}, headers=auth())
    assert r.status_code == 200
    results = r.json()["results"]
    assert [x["customerId"] for x in results] == ["cust-1", "ghost", "cust-2"]
    assert results[1] == {"customerId": "ghost", "missing": True}
    assert results[0]["missing"] is False and results[2]["missing"] is False


def test_all_missing(client):
    r = client.post(URL, json={"customerIds": ["nobody"]}, headers=auth())
    assert r.status_code == 200
    assert r.json() == {"results": [{"customerId": "nobody", "missing": True}]}


def test_batch_boundaries_1_and_100_accepted(client):
    assert client.post(URL, json={"customerIds": ["a1"]}, headers=auth()).status_code == 200
    ids = [f"c{i}" for i in range(100)]
    r = client.post(URL, json={"customerIds": ids}, headers=auth())
    assert r.status_code == 200 and len(r.json()["results"]) == 100


def test_ids_are_trimmed(client):
    r = client.post(URL, json={"customerIds": ["  cust-1\t"]}, headers=auth())
    assert r.status_code == 200 and r.json()["results"][0]["customerId"] == "cust-1"


@pytest.mark.parametrize("claims", [
    {"role": "admin"},
    {"role": "compliance"},
    {"role": ["user", "compliance"]},
    {"scope": "openid preferences:audit"},
    {"scope": ["preferences:audit"]},
])
def test_authorized_principals(client, claims):
    token = make_token({"sub": "svc", "exp": int(time.time()) + 60, **claims})
    assert client.post(URL, json={"customerIds": ["cust-1"]}, headers=auth(token)).status_code == 200


# ---- AC-3 / AC-7: batch limits and input validation -------------------------------------------

def test_empty_batch_rejected(client):
    r = client.post(URL, json={"customerIds": []}, headers=auth())
    assert_problem(r, 400, "Bad Request")


def test_101_ids_rejected_and_nothing_processed(client, monkeypatch):
    calls = []
    monkeypatch.setattr(audit_controller, "lookup", lambda cid: calls.append(cid))
    ids = [f"c{i}" for i in range(101)]
    r = client.post(URL, json={"customerIds": ids}, headers=auth())
    assert_problem(r, 400, "Bad Request")
    assert calls == []


@pytest.mark.parametrize("body", [
    {},
    {"customerIds": None},
    {"customerIds": "cust-1"},
    {"customerIds": [1, 2]},
    {"customerIds": [None]},
    {"customerIds": [["cust-1"]]},
    {"customerIds": [""]},
    {"customerIds": ["   "]},
    {"customerIds": ["../etc/passwd"]},
    {"customerIds": ["a b"]},
    {"customerIds": ["ok\nINJECTED log line"]},
    {"customerIds": ["-leading-dash"]},
    {"customerIds": ["x" * 65]},
    {"customerIds": ["cust-1", "cust-1"]},
    {"customerIds": ["cust-1", " cust-1 "]},
    {"customerIds": ["cust-1"], "extra": True},
    [],
    "text",
])
def test_invalid_payloads_rejected_with_problem_details(client, body):
    r = client.post(URL, json=body, headers=auth())
    assert_problem(r, 400, "Bad Request")


@pytest.mark.parametrize("raw", [b"", b"{not json", b'{"customerIds": ["a"]', b"\xff\xfe"])
def test_malformed_json_rejected(client, raw):
    r = client.post(URL, content=raw, headers={**auth(), "Content-Type": "application/json"})
    assert_problem(r, 400, "Bad Request")


def test_invalid_input_is_not_echoed_in_error(client):
    bad = "evil\nINJECTED<script>"
    r = client.post(URL, json={"customerIds": [bad], "sneaky_key_xyz": 1}, headers=auth())
    assert r.status_code == 400
    assert "INJECTED" not in r.text and "sneaky_key_xyz" not in r.text


# ---- AC-4: authentication ---------------------------------------------------------------------

def _expect_401(resp):
    body = assert_problem(resp, 401, "Unauthorized")
    assert resp.headers["www-authenticate"] == "Bearer"
    return body


def test_missing_authorization_header(client):
    _expect_401(client.post(URL, json={"customerIds": ["cust-1"]}))


@pytest.mark.parametrize("header", ["", "Bearer", "Bearer ", "Basic abc", "Bearer a b", "token-only"])
def test_malformed_authorization_header(client, header):
    _expect_401(client.post(URL, json={"customerIds": ["cust-1"]}, headers={"Authorization": header}))


@pytest.mark.parametrize("token", ["garbage", "a.b", "a.b.c.d", "...", "!!!.@@@.###", "e30.e30."])
def test_malformed_token(client, token):
    _expect_401(client.post(URL, json={"customerIds": ["cust-1"]}, headers=auth(token)))


def test_expired_token(client):
    token = make_token({"sub": "s", "role": "admin", "exp": int(time.time()) - 1})
    _expect_401(client.post(URL, json={"customerIds": ["cust-1"]}, headers=auth(token)))


def test_invalid_signature(client):
    token = make_token(secret="some-other-secret")
    _expect_401(client.post(URL, json={"customerIds": ["cust-1"]}, headers=auth(token)))


def test_tampered_payload_rejected(client):
    h, _, s = make_token({"sub": "s", "role": "user", "exp": int(time.time()) + 600}).split(".")
    forged = _b64(json.dumps({"sub": "s", "role": "admin", "exp": int(time.time()) + 600}).encode())
    _expect_401(client.post(URL, json={"customerIds": ["cust-1"]}, headers=auth(f"{h}.{forged}.{s}")))


@pytest.mark.parametrize("header", [{"alg": "none", "typ": "JWT"}, {"alg": "HS512"}, {"alg": "RS256"}, {}])
def test_non_hs256_algorithms_rejected(client, header):
    _expect_401(client.post(URL, json={"customerIds": ["cust-1"]}, headers=auth(make_token(header=header))))


def test_alg_none_unsigned_token_rejected(client):
    token = make_token(header={"alg": "none"}, sign=False)
    _expect_401(client.post(URL, json={"customerIds": ["cust-1"]}, headers=auth(token)))


@pytest.mark.parametrize("claims", [
    {"sub": "s", "role": "admin"},
    {"sub": "s", "role": "admin", "exp": "tomorrow"},
    {"sub": "s", "role": "admin", "exp": True},
    {"role": "admin", "exp": int(time.time()) + 600},
    {"sub": "s", "role": "admin", "exp": int(time.time()) + 600, "nbf": int(time.time()) + 600},
], ids=["no-exp", "str-exp", "bool-exp", "no-sub", "nbf-future"])
def test_invalid_claims_rejected(client, claims):
    _expect_401(client.post(URL, json={"customerIds": ["cust-1"]}, headers=auth(make_token(claims))))


def test_nan_exp_rejected(client):
    h = _b64(b'{"alg":"HS256"}')
    p = _b64(b'{"sub":"s","role":"admin","exp":NaN}')
    sig = _b64(hmac.new(SECRET.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest())
    _expect_401(client.post(URL, json={"customerIds": ["cust-1"]}, headers=auth(f"{h}.{p}.{sig}")))


def test_auth_checked_before_body_validation(client):
    _expect_401(client.post(URL, content=b"{garbage", headers={"Content-Type": "application/json"}))
    _expect_401(client.post(URL, json={"customerIds": []}))


# ---- AC-6: authorization ----------------------------------------------------------------------

@pytest.mark.parametrize("claims", [
    {"role": "customer"},
    {"role": []},
    {"role": ["admin-ish", "Admin"]},
    {"scope": "preferences:read"},
    {"scope": "preferences:audit2"},
    {"role": 5, "scope": 7},
    {},
])
def test_insufficient_permission_is_403(client, claims):
    token = make_token({"sub": "cust-1", "exp": int(time.time()) + 600, **claims})
    r = client.post(URL, json={"customerIds": ["cust-1"]}, headers=auth(token))
    assert_problem(r, 403, "Forbidden")


def test_authorization_checked_before_body_validation(client):
    token = make_token({"sub": "c", "role": "customer", "exp": int(time.time()) + 600})
    assert_problem(client.post(URL, json={"customerIds": []}, headers=auth(token)), 403, "Forbidden")


def test_forbidden_request_does_no_lookup(client, monkeypatch):
    calls = []
    monkeypatch.setattr(audit_controller, "lookup", lambda cid: calls.append(cid))
    token = make_token({"sub": "c", "role": "customer", "exp": int(time.time()) + 600})
    client.post(URL, json={"customerIds": ["cust-1"]}, headers=auth(token))
    assert calls == []


# ---- AC-5: idempotent and read-only -----------------------------------------------------------

def test_repeated_requests_identical_and_store_unmodified(client):
    before = copy.deepcopy(store.PREFERENCE_STORE)
    payload = {"customerIds": ["cust-1", "ghost", "cust-2"]}
    first = client.post(URL, json=payload, headers=auth())
    second = client.post(URL, json=payload, headers=auth())
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert store.PREFERENCE_STORE == before
    assert "ghost" not in store.PREFERENCE_STORE


# ---- Secret handling / no token leakage -------------------------------------------------------

def test_unconfigured_secret_fails_closed_with_500(client, monkeypatch, caplog):
    monkeypatch.delenv(SECRET_ENV)
    token = make_token()
    with caplog.at_level(logging.DEBUG):
        r = client.post(URL, json={"customerIds": ["cust-1"]}, headers=auth(token))
    assert_problem(r, 500, "Internal Server Error")
    assert token not in r.text and token not in caplog.text


def test_empty_secret_fails_closed(client, monkeypatch):
    monkeypatch.setenv(SECRET_ENV, "")
    assert_problem(client.post(URL, json={"customerIds": ["cust-1"]}, headers=auth()), 500, "Internal Server Error")


@pytest.mark.parametrize("scenario", ["valid", "bad_sig", "expired", "forbidden", "malformed_body"])
def test_token_and_secret_never_leak_in_logs_or_responses(client, caplog, scenario):
    now = int(time.time())
    token = {
        "valid": make_token(),
        "bad_sig": make_token(secret="wrong-secret-value"),
        "expired": make_token({"sub": "s", "role": "admin", "exp": now - 5}),
        "forbidden": make_token({"sub": "s", "role": "customer", "exp": now + 60}),
        "malformed_body": make_token(),
    }[scenario]
    body = b"{bad" if scenario == "malformed_body" else b'{"customerIds": ["cust-1"]}'
    with caplog.at_level(logging.DEBUG):
        r = client.post(URL, content=body, headers={**auth(token), "Content-Type": "application/json"})
    sig = token.split(".")[2]
    for text in (r.text, caplog.text, json.dumps(dict(r.headers))):
        assert token not in text and sig not in text
        assert SECRET not in text and "wrong-secret-value" not in text


# ---- Wiring -----------------------------------------------------------------------------------

def test_route_is_documented_in_openapi(client):
    spec = client.get("/openapi.json").json()
    assert "post" in spec["paths"][URL]
    assert "requestBody" in spec["paths"][URL]["post"]


def test_existing_forms_routes_still_work(client):
    assert client.get("/api/v1/forms").status_code == 200
