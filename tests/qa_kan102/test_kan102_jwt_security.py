"""ADR-02 (JWT authentication and role/scope authorisation) and security hygiene.

Uses a dummy secret only (see kan102_support.SECRET). Tokens are forged locally with hmac/hashlib.
"""
import hashlib
import time
import types

import pytest

from app.security import jwt_hs256
from kan102_support import (
    DROP, SECRET, SECRET_ENV, URL, assert_problem, auth, b64, b64_decode, bearer, claims, make_token, sign,
)

BODY = {"customerIds": ["cust-1"]}
RAW_HEADER = {"alg": "HS256", "typ": "JWT"}


def call(client, token=None, headers=None, body=None):
    h = headers if headers is not None else (bearer(token) if token is not None else {})
    return client.post(URL, json=BODY if body is None else body, headers=h)


def status_for(client, **claim_overrides):
    return call(client, make_token(claims(**claim_overrides))).status_code


# ---- Authorization header handling ----------------------------------------------------------------

def test_missing_authorization_header_is_401(client):
    r = call(client)
    assert_problem(r, 401)
    assert r.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("value", [
    "Bearer", "Bearer ", "bearer", "Basic dXNlcjpwYXNz", "Token abc.def.ghi", "Bearer  a.b.c", "Bearer a.b.c extra",
    "BearerA.B.C", "", " ", "null", "undefined", "Bearer null", "Bearer undefined", "Bearer ...", "Bearer .",
])
def test_malformed_authorization_header_is_401(client, value):
    r = call(client, headers={"Authorization": value})
    assert_problem(r, 401)
    assert r.headers["www-authenticate"] == "Bearer"


def test_raw_token_without_scheme_is_401(client):
    assert_problem(call(client, headers={"Authorization": make_token()}), 401)


@pytest.mark.parametrize("scheme", ["Bearer", "bearer", "BEARER", "bEaReR"])
def test_scheme_name_is_case_insensitive(client, scheme):
    assert call(client, headers={"Authorization": f"{scheme} {make_token()}"}).status_code == 200


def test_non_ascii_bytes_in_authorization_header_are_401_not_500(client):
    for raw in (b"Bearer \xff\xfe\xfd", b"Bearer \xc3\xa9.\xc3\xa9.\xc3\xa9", b"\xff"):
        assert_problem(call(client, headers={"Authorization": raw}), 401)


def test_token_must_come_from_authorization_header_only(client):
    tok = make_token()
    assert_problem(client.post(URL + "?access_token=" + tok, json=BODY), 401)
    assert_problem(client.post(URL + "?token=" + tok, json=BODY), 401)
    assert_problem(client.post(URL, json=BODY, headers={"Cookie": "token=" + tok, "X-Authorization": "Bearer " + tok}), 401)
    assert_problem(client.post(URL, json={"customerIds": ["cust-1"], "access_token": tok}), 401)


def test_duplicate_authorization_headers_invalid_first_is_401(client):
    r = client.post(URL, json=BODY, headers=[("Authorization", "Bearer bad.bad.bad"), ("Authorization", "Bearer " + make_token())])
    assert r.status_code == 401


def test_duplicate_authorization_headers_never_server_error(client):
    r = client.post(URL, json=BODY, headers=[("Authorization", "Bearer " + make_token()), ("Authorization", "Bearer bad")])
    assert r.status_code in (200, 401)


# ---- token structure ------------------------------------------------------------------------------

@pytest.mark.parametrize("token", [
    "", "a", "a.b", "a.b.c.d", "..", "a..c", ".b.c", "a.b.", "....", "a b.c.d", "a.b.c\n", "e30.e30.e30",
])
def test_structurally_invalid_tokens_are_401(client, token):
    assert_problem(call(client, headers={"Authorization": "Bearer " + token}), 401)


def test_valid_token_with_extra_segment_or_trailing_dot_is_401(client):
    t = make_token()
    assert_problem(call(client, t + ".extra"), 401)
    assert_problem(call(client, t + "."), 401)


def test_valid_token_baseline_is_accepted(client):
    assert call(client, make_token()).status_code == 200


# ---- algorithm confusion --------------------------------------------------------------------------

BAD_HEADERS = [
    {"alg": "none", "typ": "JWT"}, {"alg": "None"}, {"alg": "NONE"}, {"alg": "nOnE"}, {"alg": ""}, {"alg": None},
    {"alg": "hs256"}, {"alg": "HS256 "}, {"alg": " HS256"}, {"alg": ["HS256"]}, {"alg": {"a": "HS256"}}, {"alg": 256},
    {"alg": "RS256"}, {"alg": "ES256"}, {"alg": "PS256"}, {"alg": "EdDSA"}, {"typ": "JWT"}, {},
]


@pytest.mark.parametrize("header", BAD_HEADERS, ids=[f"hdr{i}" for i in range(len(BAD_HEADERS))])
def test_non_hs256_or_malformed_alg_header_is_401(client, header):
    # signed correctly with HMAC-SHA256 so only the alg header can be the reason for rejection
    assert_problem(call(client, make_token(header=header)), 401)


@pytest.mark.parametrize("alg,digest", [("HS384", hashlib.sha384), ("HS512", hashlib.sha512)])
def test_hs384_hs512_tokens_with_correct_signature_are_rejected(client, alg, digest):
    tok = make_token(header={"alg": alg, "typ": "JWT"}, digest=digest)
    assert_problem(call(client, tok), 401)


def test_alg_none_unsigned_tokens_are_rejected(client):
    for sig in ("", sign("x.y"), b64(b"\x00" * 32)):
        tok = make_token(header={"alg": "none"}, signature=sig)
        assert_problem(call(client, tok), 401)


def test_rs256_header_with_hmac_signature_key_confusion_is_rejected(client):
    assert_problem(call(client, make_token(header={"alg": "RS256", "typ": "JWT"})), 401)


@pytest.mark.parametrize("header", [b"[]", b"\"HS256\"", b"null", b"12", b"not json", b"\xff\xfe", b""])
def test_non_object_header_segment_is_401(client, header):
    assert_problem(call(client, make_token(header=header)), 401)


def test_header_alg_ok_with_extra_header_params_is_accepted_only_when_signature_matches(client):
    ok = make_token(header={"alg": "HS256", "typ": "JWT", "kid": "k1", "x": [1]})
    assert call(client, ok).status_code == 200
    forged = make_token(header={"alg": "HS256", "kid": "../../dev/null"}, secret="")
    assert_problem(call(client, forged), 401)


# ---- tampering ------------------------------------------------------------------------------------

def test_payload_tampered_to_escalate_role_is_401(client):
    low = make_token(claims(role="user"))
    h, _, s = low.split(".")
    assert call(client, low).status_code == 403
    forged_payload = b64(b"{\"sub\":\"qa-auditor\",\"role\":\"admin\",\"exp\":9999999999}")
    assert_problem(call(client, f"{h}.{forged_payload}.{s}"), 401)


def test_signature_bit_flip_in_every_region_is_401(client):
    h, p, s = make_token().split(".")
    raw = bytearray(b64_decode(s))
    for index in (0, 7, 15, 31):
        mutated = bytearray(raw)
        mutated[index] ^= 0x01
        assert_problem(call(client, f"{h}.{p}.{b64(bytes(mutated))}"), 401)


BANG = chr(33) * 4
SIG_MUTATIONS = {
    "half": lambda s: s[: len(s) // 2],
    "empty": lambda s: "",
    "doubled": lambda s: s + s,
    "not_base64": lambda s: BANG,
    "zeros": lambda s: b64(b"\x00" * 32),
    "ones": lambda s: b64(b"\xff" * 32),
    "one_byte_short": lambda s: b64(b64_decode(s)[:-1]),
    "one_byte_long": lambda s: b64(b64_decode(s) + b"\x00"),
    "reversed": lambda s: s[::-1],
    "trailing_nul": lambda s: s + "\x00",
}


@pytest.mark.parametrize("name", sorted(SIG_MUTATIONS))
def test_signature_manipulations_are_401(client, name):
    h, p, s = make_token().split(".")
    assert_problem(call(client, f"{h}.{p}.{SIG_MUTATIONS[name](s)}"), 401)


def test_header_modified_after_signing_is_401(client):
    _, p, s = make_token().split(".")
    other_header = b64(b"{\"alg\":\"HS256\",\"typ\":\"JWT\",\"x\":1}")
    assert_problem(call(client, f"{other_header}.{p}.{s}"), 401)


def test_token_signed_with_a_different_secret_is_401(client):
    for secret in ("other", SECRET + "x", SECRET[:-1], SECRET.upper(), " " + SECRET, "x"):
        assert_problem(call(client, make_token(secret=secret)), 401)


@pytest.mark.parametrize("payload", [b"%%%%", b"[]", b"\"x\"", b"null", b"42", b"", b"\xff\xfe", b"{\"sub\":", b"{}"])
def test_validly_signed_but_malformed_payload_is_401(client, payload):
    assert_problem(call(client, make_token(payload=payload)), 401)


def test_signed_payload_segment_that_is_not_base64_is_401(client):
    assert_problem(call(client, make_token(payload="%%%not-base64%%%")), 401)
    non_ascii = ("Bearer " + make_token(payload=chr(233) * 2)).encode("utf-8")
    assert_problem(call(client, headers={"Authorization": non_ascii}), 401)


# ---- claims: exp / nbf / sub ----------------------------------------------------------------------

NOW = 1_800_000_000


@pytest.fixture
def frozen(monkeypatch):
    """Freeze the clock seen by the JWT module so boundaries are exact."""
    monkeypatch.setattr(jwt_hs256, "time", types.SimpleNamespace(time=lambda: float(NOW)))
    return NOW


def test_exp_boundary_exactly_now_is_expired_one_second_later_is_valid(client, frozen):
    assert_problem(call(client, make_token(claims(exp=NOW))), 401)
    assert_problem(call(client, make_token(claims(exp=NOW - 1))), 401)
    assert call(client, make_token(claims(exp=NOW + 1))).status_code == 200
    assert call(client, make_token(claims(exp=NOW + 0.5))).status_code == 200
    assert_problem(call(client, make_token(claims(exp=NOW - 0.001))), 401)


def test_nbf_boundary_exactly_now_is_valid_one_second_ahead_is_not(client, frozen):
    assert call(client, make_token(claims(exp=NOW + 600, nbf=NOW))).status_code == 200
    assert call(client, make_token(claims(exp=NOW + 600, nbf=NOW - 1))).status_code == 200
    assert_problem(call(client, make_token(claims(exp=NOW + 600, nbf=NOW + 1))), 401)
    assert_problem(call(client, make_token(claims(exp=NOW + 600, nbf=NOW + 0.001))), 401)


@pytest.mark.parametrize("exp", [
    DROP, None, "9999999999", "", "never", True, False, float("nan"), float("inf"), float("-inf"), [], [9999999999],
    {}, {"v": 9999999999}, 0, -1, 1, -9999999999,
], ids=lambda v: "drop" if v is DROP else repr(v)[:20])
def test_invalid_or_non_numeric_exp_is_401(client, exp):
    assert_problem(call(client, make_token(claims(exp=exp))), 401)


@pytest.mark.parametrize("literal", [b"1e400", b"-1e400", b"1E999", b"0x10", b"+5", b"09", b".5", b"5."])
def test_exp_numeric_literal_oddities_never_grant_access(client, literal):
    payload = b"{\"sub\":\"s\",\"role\":\"admin\",\"exp\":" + literal + b"}"
    r = call(client, make_token(payload=payload))
    assert r.status_code == 401, r.text


def test_exp_integer_beyond_float_range_is_handled_without_server_error(client):
    """exp = 10**400 is a finite JSON integer but overflows float(); must not surface as a 5xx."""
    payload = b"{\"sub\":\"s\",\"role\":\"admin\",\"exp\":" + b"9" * 400 + b"}"
    r = call(client, make_token(payload=payload))
    assert r.status_code < 500, f"unhandled error for validly signed token: {r.status_code} {r.text[:80]}"
    if r.status_code >= 400:
        assert_problem(r, 401)


def test_nbf_integer_beyond_float_range_is_handled_without_server_error(client):
    payload = b"{\"sub\":\"s\",\"role\":\"admin\",\"exp\":9999999999,\"nbf\":" + b"9" * 400 + b"}"
    r = call(client, make_token(payload=payload))
    assert r.status_code < 500, f"unhandled error for validly signed token: {r.status_code} {r.text[:80]}"


@pytest.mark.parametrize("nbf", ["0", "", True, False, float("nan"), float("inf"), [], {}, [0]],
                         ids=lambda v: repr(v)[:20])
def test_invalid_nbf_is_401(client, nbf):
    assert_problem(call(client, make_token(claims(nbf=nbf))), 401)


def test_past_nbf_and_float_exp_are_accepted(client):
    assert call(client, make_token(claims(nbf=int(time.time()) - 60))).status_code == 200
    assert call(client, make_token(claims(exp=time.time() + 600.5))).status_code == 200


def test_future_nbf_is_401(client):
    assert_problem(call(client, make_token(claims(nbf=int(time.time()) + 3600))), 401)


@pytest.mark.parametrize("sub", [DROP, None, "", 123, 0, True, False, [], ["a"], {}, {"id": 1}, 1.5],
                         ids=lambda v: "drop" if v is DROP else repr(v)[:20])
def test_missing_or_non_string_sub_is_401(client, sub):
    assert_problem(call(client, make_token(claims(sub=sub))), 401)


@pytest.mark.parametrize("sub", ["x", "user@example.test", "\u00fcser", " ", "a" * 5000])
def test_any_non_empty_string_sub_is_accepted(client, sub):
    assert call(client, make_token(claims(sub=sub))).status_code == 200


def test_unknown_extra_claims_do_not_affect_access(client):
    assert call(client, make_token(claims(iss="x", aud="y", iat=1, jti="z", custom={"a": 1}))).status_code == 200
    assert_problem(call(client, make_token(claims(role="user", iss="x", admin=True, is_admin=True, roles=["admin"]))), 403)


def test_token_size_limit_boundary_8192(client):
    def tok(n):
        return make_token(claims(pad="x" * n))
    lo, hi = 0, 20000
    while lo < hi:  # largest padding whose token is still within the limit
        mid = (lo + hi + 1) // 2
        lo, hi = (mid, hi) if len(tok(mid)) <= 8192 else (lo, mid - 1)
    ok, too_big = tok(lo), tok(lo + 1)
    assert 8190 <= len(ok) <= 8192 and len(too_big) > 8192
    assert call(client, ok).status_code == 200
    assert_problem(call(client, too_big), 401)


def test_very_large_token_is_401_not_500(client):
    assert_problem(call(client, make_token(claims(pad="x" * 2_000_000))), 401)
    assert_problem(call(client, "a." * 100_000 + "a"), 401)


# ---- authorisation: role / scope matrix (ADR-02) --------------------------------------------------

ALLOWED = [
    ("role=admin", dict(role="admin")),
    ("role=compliance", dict(role="compliance")),
    ("role list with admin", dict(role=["user", "admin"])),
    ("role list compliance only", dict(role=["compliance"])),
    ("role list with junk members", dict(role=[1, None, {"a": 1}, "admin"])),
    ("scope string exact", dict(role="user", scope="preferences:audit")),
    ("scope space delimited", dict(role="user", scope="read preferences:audit write")),
    ("scope list", dict(role="user", scope=["preferences:audit"])),
    ("scope list among others", dict(role="user", scope=["read", "preferences:audit"])),
    ("scope without any role claim", dict(role=DROP, scope="preferences:audit")),
    ("admin role and unrelated scope", dict(role="admin", scope="something:else")),
    ("insufficient role but audit scope", dict(role="viewer", scope="preferences:audit")),
    ("admin role with junk scope type", dict(role="admin", scope=12345)),
]
DENIED = [
    ("role=user", dict(role="user")),
    ("no role no scope", dict(role=DROP)),
    ("role uppercase", dict(role="ADMIN")),
    ("role capitalised", dict(role="Admin")),
    ("role compliance uppercase", dict(role="COMPLIANCE")),
    ("role administrator", dict(role="administrator")),
    ("role superadmin", dict(role="superadmin")),
    ("role comma separated", dict(role="admin,user")),
    ("role empty string", dict(role="")),
    ("role empty list", dict(role=[])),
    ("role list without admin", dict(role=["user", "viewer"])),
    ("role list uppercase admin", dict(role=["ADMIN"])),
    ("role dict", dict(role={"admin": True})),
    ("role true", dict(role=True)),
    ("role null", dict(role=None)),
    ("role number", dict(role=1)),
    ("role nested list", dict(role=[["admin"]])),
    ("scope near miss suffix", dict(role="user", scope="preferences:audit:extra")),
    ("scope near miss prefix", dict(role="user", scope="xpreferences:audit")),
    ("scope near miss auditor", dict(role="user", scope="preferences:auditor")),
    ("scope wildcard", dict(role="user", scope="preferences:*")),
    ("scope wildcard all", dict(role="user", scope="*")),
    ("scope uppercase", dict(role="user", scope="PREFERENCES:AUDIT")),
    ("scope read only", dict(role="user", scope="preferences:read")),
    ("scope prefix only", dict(role="user", scope="preferences")),
    ("scope comma separated", dict(role="user", scope="read,preferences:audit")),
    ("scope empty list", dict(role="user", scope=[])),
    ("scope dict", dict(role="user", scope={"preferences:audit": True})),
    ("scope true", dict(role="user", scope=True)),
    ("scope nested list", dict(role="user", scope=[["preferences:audit"]])),
    ("scope in scp claim", dict(role="user", scp="preferences:audit")),
    ("scope in scopes claim", dict(role="user", scopes=["preferences:audit"])),
    ("scope in permissions claim", dict(role="user", permissions=["preferences:audit"])),
    ("admin in roles claim", dict(role="user", roles=["admin"])),
    ("admin boolean flags", dict(role="user", admin=True, is_admin=True, isAdmin=True)),
    ("admin in sub", dict(role="user", sub="admin")),
]


@pytest.mark.parametrize("name,overrides", ALLOWED, ids=[n for n, _ in ALLOWED])
def test_authorised_principals_get_200(client, name, overrides):
    assert call(client, make_token(claims(**overrides))).status_code == 200


@pytest.mark.parametrize("name,overrides", DENIED, ids=[n for n, _ in DENIED])
def test_unauthorised_principals_get_403_problem_json(client, name, overrides, lookup_spy):
    assert_problem(call(client, make_token(claims(**overrides))), 403)
    assert lookup_spy == []


def test_403_does_not_reveal_required_role_or_scope(client):
    r = call(client, make_token(claims(role="user")))
    text = r.text.lower()
    assert "preferences:audit" not in text and "compliance" not in text and "admin" not in text


def test_401_and_403_use_different_statuses_for_unauthenticated_vs_unauthorised(client):
    assert call(client, make_token(claims(role="user"))).status_code == 403
    assert call(client, make_token(claims(role="user"), secret="x")).status_code == 401


# ---- secret handling: fail closed -----------------------------------------------------------------

@pytest.mark.parametrize("mode", ["unset", "empty"])
def test_missing_or_empty_secret_fails_closed_with_generic_500(client, monkeypatch, mode):
    token = make_token()  # signed with the dummy secret, then the server loses its secret
    if mode == "unset":
        monkeypatch.delenv(SECRET_ENV, raising=False)
    else:
        monkeypatch.setenv(SECRET_ENV, "")
    r = call(client, token)
    body = assert_problem(r, 500)
    blob = (r.text + str(dict(r.headers))).lower()
    assert SECRET.lower() not in blob and "jwt_secret" not in blob and "secret" not in body["detail"].lower()
    assert "results" not in r.text


@pytest.mark.parametrize("forge_secret", ["", "None", "null", "undefined", "secret", "changeme"])
def test_unset_secret_never_accepts_tokens_forged_with_guessable_keys(client, monkeypatch, forge_secret):
    monkeypatch.delenv(SECRET_ENV, raising=False)
    r = call(client, make_token(secret=forge_secret))
    assert r.status_code in (401, 500)
    assert "results" not in r.text


def test_empty_secret_does_not_validate_tokens_signed_with_empty_key(client, monkeypatch):
    monkeypatch.setenv(SECRET_ENV, "")
    r = call(client, make_token(secret=""))
    assert r.status_code == 500 and "results" not in r.text


def test_unauthenticated_request_with_unset_secret_never_succeeds(client, monkeypatch):
    monkeypatch.delenv(SECRET_ENV, raising=False)
    r = call(client)
    assert r.status_code in (401, 500)


def test_secret_is_read_at_call_time_and_rotation_invalidates_old_tokens(client, monkeypatch):
    old = make_token()
    assert call(client, old).status_code == 200
    monkeypatch.setenv(SECRET_ENV, "rotated-dummy-secret-qa")
    assert_problem(call(client, old), 401)
    assert call(client, make_token(secret="rotated-dummy-secret-qa")).status_code == 200


def test_no_default_secret_baked_into_the_module():
    assert not hasattr(jwt_hs256, "DEFAULT_SECRET")
    import inspect
    src = inspect.getsource(jwt_hs256)
    assert "environ.get(SECRET_ENV_VAR, \"\")" in src or "getenv" in src
    assert SECRET not in src


# ---- check order: 401 then 403 then 400, body not parsed before auth --------------------------------

def test_body_is_not_parsed_before_authentication_or_authorisation(client, monkeypatch):
    from app.api import audit_controller
    calls = []
    real = audit_controller.BulkPreferencesAuditRequest.model_validate_json

    def spy(*a, **k):
        calls.append(1)
        return real(*a, **k)

    monkeypatch.setattr(audit_controller.BulkPreferencesAuditRequest, "model_validate_json", spy)
    bad_body = b"{this is not json"
    h = {"Content-Type": "application/json"}
    client.post(URL, content=bad_body, headers=h)                                        # 401
    client.post(URL, content=bad_body, headers={**h, **bearer("a.b.c")})                 # 401
    client.post(URL, content=bad_body, headers={**h, **auth(role="user")})               # 403
    assert calls == []
    assert client.post(URL, content=bad_body, headers={**h, **auth()}).status_code == 400
    assert calls == [1]


def test_check_order_matrix(client):
    bad = {"customerIds": []}
    assert call(client, body=bad).status_code == 401
    assert call(client, make_token(secret="x"), body=bad).status_code == 401
    assert call(client, make_token(claims(role="user")), body=bad).status_code == 403
    assert call(client, make_token(), body=bad).status_code == 400


def test_unset_secret_error_precedes_body_validation(client, monkeypatch):
    monkeypatch.delenv(SECRET_ENV, raising=False)
    assert call(client, make_token(), body={"customerIds": []}).status_code == 500


# ---- information leakage --------------------------------------------------------------------------

def _scenarios():
    good = make_token()
    low = make_token(claims(role="user"))
    expired = make_token(claims(exp=1))
    badsig = make_token(secret="not-the-secret")
    return [
        ("ok", good, BODY), ("403", low, BODY), ("expired", expired, BODY), ("badsig", badsig, BODY),
        ("bad body", good, {"customerIds": ["bad id"]}), ("dup", good, {"customerIds": ["a", "a"]}),
        ("extra", good, {"customerIds": ["a"], "x": 1}), ("empty", good, {"customerIds": []}),
    ]


def test_tokens_and_secret_never_appear_in_responses_or_logs(client, caplog):
    import logging
    caplog.set_level(logging.DEBUG)
    sensitive = {SECRET}
    for _, token, body in _scenarios():
        sensitive.update({token, token.split(".")[1], token.split(".")[2], "Bearer " + token})
        r = client.post(URL, json=body, headers=bearer(token))
        blob = r.text + "\n".join(f"{k}: {v}" for k, v in r.headers.items())
        for secret_value in sensitive:
            assert secret_value not in blob
    r = client.post(URL, json=BODY, headers={"Authorization": "Bearer garbage-token-value-XYZ"})
    assert "garbage-token-value-XYZ" not in r.text
    logs = caplog.text
    assert logs, "expected the JWT module to log failures at INFO"
    for secret_value in sensitive | {"garbage-token-value-XYZ"}:
        assert secret_value not in logs


def test_secret_never_logged_when_misconfigured(client, monkeypatch, caplog):
    import logging
    caplog.set_level(logging.DEBUG)
    monkeypatch.setenv(SECRET_ENV, "")
    tok = make_token()
    call(client, tok)
    assert SECRET not in caplog.text and tok not in caplog.text


def test_all_401_responses_are_indistinguishable_no_oracle(client):
    variants = [
        None, "garbage", make_token(secret="x"), make_token(claims(exp=1)), make_token(header={"alg": "none"}),
        make_token(claims(sub=DROP)), make_token(claims(nbf=4102444800)), make_token(payload=b"[]"), "a.b",
    ]
    bodies = set()
    for tok in variants:
        r = call(client, tok)
        assert_problem(r, 401)
        bodies.add(r.text)
        assert r.headers["www-authenticate"] == "Bearer"
    assert len(bodies) == 1


def test_error_responses_do_not_expose_stack_traces_or_internals(client):
    leaks = ("traceback", "file \"", ".py", "pydantic", "hmac", "jwt_hs256", "audit_controller", "line ")
    cases = [call(client), call(client, make_token(claims(role="user"))), call(client, make_token(), body={}),
             call(client, make_token(), body={"customerIds": ["../x"]})]
    for r in cases:
        low = r.text.lower()
        for needle in leaks:
            assert needle not in low, (needle, r.text)


def test_no_wildcard_cors_or_credentialed_headers(client):
    r = client.post(URL, json=BODY, headers={**auth(), "Origin": "https://evil.example"})
    assert r.status_code == 200
    assert "access-control-allow-origin" not in r.headers
    assert "set-cookie" not in r.headers
