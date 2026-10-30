"""Smoke tests against a real uvicorn process on 127.0.0.1 (dummy secret, no external network).

Covers what TestClient cannot: real HTTP framing, header size handling and process log output.
Note: the live process has an empty in-memory store (nothing writes to it), so every ID is missing.
"""
import http.client
import importlib.util
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from kan102_support import SECRET, SECRET_ENV, URL, claims, make_token

REPO = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(importlib.util.find_spec("uvicorn") is None, reason="uvicorn not installed")


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Live:
    def __init__(self, tmp_path, secret):
        self.port = _free_port()
        self.log_path = tmp_path / "uvicorn.log"
        env = {k: v for k, v in os.environ.items() if k != SECRET_ENV}
        if secret is not None:
            env[SECRET_ENV] = secret
        self.log = open(self.log_path, "wb")
        self.proc = subprocess.Popen(
            [sys.executable, "-B", "-m", "uvicorn", "app.server:app", "--host", "127.0.0.1", "--port", str(self.port)],
            cwd=str(REPO), env=env, stdout=self.log, stderr=subprocess.STDOUT,
        )
        deadline = time.time() + 30
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError("uvicorn exited early: " + self.log_path.read_text(errors="replace"))
            try:
                socket.create_connection(("127.0.0.1", self.port), timeout=0.5).close()
                return
            except OSError:
                time.sleep(0.2)
        raise RuntimeError("uvicorn did not start")

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=20)
        try:
            data = body if isinstance(body, (bytes, type(None))) else json.dumps(body).encode()
            hdrs = {"Content-Type": "application/json"}
            hdrs.update(headers or {})
            conn.request(method, path, body=data, headers=hdrs)
            resp = conn.getresponse()
            return resp.status, {k.lower(): v for k, v in resp.getheaders()}, resp.read()
        finally:
            conn.close()

    def logs(self):
        self.log.flush()
        return self.log_path.read_text(errors="replace")

    def stop(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.log.close()


@pytest.fixture(scope="module")
def live(tmp_path_factory):
    server = Live(tmp_path_factory.mktemp("live"), SECRET)
    yield server
    server.stop()


def bearer_header(token):
    return {"Authorization": "Bearer " + token}


def test_live_happy_path_returns_missing_for_unseeded_store(live):
    status, headers, body = live.request("POST", URL, {"customerIds": ["live-1", "live-2"]}, bearer_header(make_token()))
    assert status == 200 and headers["content-type"].startswith("application/json")
    assert json.loads(body) == {"results": [{"customerId": "live-1", "missing": True},
                                            {"customerId": "live-2", "missing": True}]}


def test_live_repeated_calls_are_byte_identical(live):
    outs = {live.request("POST", URL, {"customerIds": ["live-1"]}, bearer_header(make_token()))[2] for _ in range(5)}
    assert len(outs) == 1


def test_live_401_is_problem_json_with_www_authenticate(live):
    status, headers, body = live.request("POST", URL, {"customerIds": ["a"]})
    assert status == 401 and headers["content-type"].startswith("application/problem+json")
    assert headers["www-authenticate"] == "Bearer"
    assert set(json.loads(body)) == {"type", "title", "status", "detail", "instance"}


def test_live_403_and_400_and_405(live):
    low = bearer_header(make_token(claims(role="user")))
    assert live.request("POST", URL, {"customerIds": ["a"]}, low)[0] == 403
    status, headers, _ = live.request("POST", URL, {"customerIds": []}, bearer_header(make_token()))
    assert status == 400 and headers["content-type"].startswith("application/problem+json")
    assert live.request("GET", URL, None, bearer_header(make_token()))[0] == 405


def test_live_101_ids_rejected(live):
    status, _, _ = live.request("POST", URL, {"customerIds": [f"id{i}" for i in range(101)]}, bearer_header(make_token()))
    assert status == 400


def test_live_token_just_over_8kb_is_401_and_under_limit_is_accepted(live):
    big = make_token(claims(pad="x" * 7000))
    small = make_token(claims(pad="x" * 5000))
    assert len(small) < 8192
    assert live.request("POST", URL, {"customerIds": ["a"]}, bearer_header(small))[0] == 200
    assert len(big) > 8192
    assert live.request("POST", URL, {"customerIds": ["a"]}, bearer_header(big))[0] == 401


def test_live_unauthenticated_large_body_gets_401_not_processed(live):
    status, _, _ = live.request("POST", URL, b"x" * (2 * 1024 * 1024))
    assert status == 401


def test_live_authenticated_garbage_body_is_400(live):
    status, headers, _ = live.request("POST", URL, b"\xff\xfe not json", bearer_header(make_token()))
    assert status == 400 and headers["content-type"].startswith("application/problem+json")


def test_live_forms_endpoints_still_served(live):
    assert live.request("GET", "/api/v1/forms")[0] == 200
    assert live.request("GET", "/api/v1/forms/customer-preferences")[0] == 200


def test_live_process_logs_never_contain_tokens_or_secret(live):
    good = make_token()
    bad = make_token(secret="not-the-secret")
    expired = make_token(claims(exp=1))
    for tok in (good, bad, expired, "garbage.token.value"):
        live.request("POST", URL, {"customerIds": ["a"]}, bearer_header(tok))
    time.sleep(0.3)
    logs = live.logs()
    assert "POST" in logs  # uvicorn access log is active, so the check below is meaningful
    for needle in (SECRET, good, bad, expired, good.split(".")[2], bad.split(".")[2], "garbage.token.value"):
        assert needle not in logs


def test_live_unset_secret_fails_closed_with_generic_500(tmp_path):
    server = Live(tmp_path, None)
    try:
        tok = make_token()
        status, headers, body = server.request("POST", URL, {"customerIds": ["a"]}, bearer_header(tok))
        assert status == 500 and headers["content-type"].startswith("application/problem+json")
        assert b"results" not in body and SECRET.encode() not in body
        assert tok not in server.logs() and SECRET not in server.logs()
    finally:
        server.stop()
