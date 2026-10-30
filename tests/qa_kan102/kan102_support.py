"""Shared helpers for the KAN-102 QA suite. Dummy secret only; no network, no real services."""
import base64
import hashlib
import hmac
import json
import time

URL = "/api/v1/customers/audit/preferences"
SECRET_ENV = "JWT_SECRET_KEY"
SECRET = "qa-kan102-dummy-secret-not-a-real-key"
PROBLEM_KEYS = {"type", "title", "status", "detail", "instance"}
DROP = object()  # sentinel: remove a claim from the default claim set


def b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def b64_decode(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


def segment(value) -> str:
    """bytes -> base64url; str -> used verbatim (raw segment); anything else -> JSON then base64url."""
    if isinstance(value, bytes):
        return b64(value)
    if isinstance(value, str):
        return value
    return b64(json.dumps(value).encode())  # allow_nan=True on purpose (NaN/Infinity literals)


def sign(signing_input: str, secret: str = SECRET, digest=hashlib.sha256) -> str:
    return b64(hmac.new(secret.encode(), signing_input.encode(), digest).digest())


def claims(**overrides) -> dict:
    base = {"sub": "qa-auditor", "role": "admin", "exp": int(time.time()) + 600}
    for key, value in overrides.items():
        if value is DROP:
            base.pop(key, None)
        else:
            base[key] = value
    return base


def make_token(payload=None, header=None, secret: str = SECRET, digest=hashlib.sha256, signature=None) -> str:
    """Build a JWT. header/payload may be dicts, raw strings (verbatim segment) or bytes."""
    h = segment(header if header is not None else {"alg": "HS256", "typ": "JWT"})
    p = segment(payload if payload is not None else claims())
    sig = signature if signature is not None else sign(f"{h}.{p}", secret, digest)
    return f"{h}.{p}.{sig}"


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def auth(**claim_overrides) -> dict:
    return bearer(make_token(claims(**claim_overrides)))


def assert_problem(resp, status: int, instance: str = URL) -> dict:
    """ADR-01: RFC 7807 problem document with the exact member set."""
    assert resp.status_code == status, resp.text
    assert resp.headers["content-type"].split(";")[0].strip() == "application/problem+json"
    body = resp.json()
    assert set(body) == PROBLEM_KEYS
    assert body["status"] == status
    assert isinstance(body["type"], str) and body["type"]
    assert isinstance(body["title"], str) and body["title"]
    assert isinstance(body["detail"], str) and body["detail"]
    assert body["instance"] == instance
    return body
