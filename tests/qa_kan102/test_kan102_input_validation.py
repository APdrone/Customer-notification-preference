"""ADR-03 (input sanitisation, batch size 1-100) and edge cases for the request body."""
import json

import pytest

from kan102_support import URL, assert_problem, auth

JSON_CT = {"Content-Type": "application/json"}


def post(client, ids, headers=None):
    return client.post(URL, json={"customerIds": ids}, headers=headers if headers is not None else auth())


def post_raw(client, raw, content_type="application/json", headers=None):
    h = dict(headers if headers is not None else auth())
    if content_type is not None:
        h["Content-Type"] = content_type
    return client.post(URL, content=raw, headers=h)


def assert_not_echoed(resp, candidate):
    """Rejected client input must never be reflected in the error document."""
    text = resp.text
    if isinstance(candidate, str) and len(candidate.strip()) >= 4:
        assert candidate not in text
        assert json.dumps(candidate)[1:-1] not in text
        assert json.dumps(candidate, ensure_ascii=False)[1:-1] not in text


# ---- batch size boundaries ------------------------------------------------------------------------

@pytest.mark.parametrize("count,status", [(0, 400), (1, 200), (2, 200), (99, 200), (100, 200), (101, 400), (102, 400)])
def test_batch_size_boundaries(client, count, status):
    r = post(client, [f"id{i}" for i in range(count)])
    assert r.status_code == status
    if status == 200:
        assert len(r.json()["results"]) == count
    else:
        assert_problem(r, 400)


# ---- ID length boundaries and accepted characters -------------------------------------------------

@pytest.mark.parametrize("cid", [
    "a", "Z", "0", "9z", "a" * 64, "A" * 64, "0" * 64, "a-b_c", "a" + "-" * 63, "a" + "_" * 63, "a-", "a_",
    "null", "NaN", "true", "undefined", "constructor", "OR", "admin", "ID-00000001",
])
def test_valid_ids_are_accepted_verbatim(client, cid):
    r = post(client, [cid])
    assert r.status_code == 200
    item = r.json()["results"][0]
    assert item["customerId"] == cid
    assert item["missing"] is (cid not in ("a", "A"))  # a and A are seeded in the test store


@pytest.mark.parametrize("length", [65, 66, 128, 10_000, 200_000])
def test_ids_longer_than_64_rejected(client, length):
    cid = "a" * length
    r = post(client, [cid])
    assert_problem(r, 400)
    assert_not_echoed(r, cid)


def test_id_exactly_64_after_trim_is_accepted_but_65_is_not(client):
    assert post(client, [" " + "a" * 64 + " "]).json()["results"][0]["customerId"] == "a" * 64
    assert_problem(post(client, [" " + "a" * 65 + " "]), 400)


@pytest.mark.parametrize("raw,expected", [
    (" cust-1 ", "cust-1"), ("\tcust-1", "cust-1"), ("cust-1\n", "cust-1"), ("\r\n cust-1 \t", "cust-1"),
])
def test_surrounding_ascii_whitespace_is_trimmed_and_resolved(client, raw, expected):
    item = post(client, [raw]).json()["results"][0]
    assert item["customerId"] == expected and item["missing"] is False


@pytest.mark.parametrize("raw", ["\u00a0cust-1", "cust-1\u2003", "\u3000cust-1"])
def test_unicode_whitespace_padding_never_leaks_into_the_returned_id(client, raw):
    """Unicode spaces are either rejected (400) or trimmed; the response id must be the clean one."""
    r = post(client, [raw])
    assert r.status_code in (200, 400)
    if r.status_code == 200:
        assert r.json()["results"][0]["customerId"] == "cust-1"
    else:
        assert_problem(r, 400)


UNSAFE_IDS = [
    "", " ", "\t", "\n", "   ", "-a", "_a", "-", "_", "a b", "a\tb", "a\nb", "a\rb", "a\x00", "\x00a", "a\x00b",
    "a\x01b", "a\x1bb", "a\x7fb", "a\x85b", "a.b", "a/b", "a" + chr(92) + "b", "..", "../", "../../etc/passwd",
    "..#..#windows#system32".replace("#", chr(92)), "%2e%2e%2f", "%00", "a%20b", "~root", "/etc/passwd", "C:" + chr(92) + "boot.ini",
    "a;b", "a,b", "a:b", "a@b", "a#b", "a$b", "a*b", "a?b", "a=b", "a&b", "a|b", "a(b)", "a[0]", "a{b}", "a+b",
    "\u00e9", "caf\u00e9", "\uff41\uff42\uff43", "\u0663", "a\u200bb", "\u202ea", "a\u0301", "\U0001F600", "\ud83d\ude00x",
    "1; DROP TABLE users;--", "x\x27 OR \x271\x27=\x271", "admin\x27--", "x\x22 OR \x221\x22=\x221",
]


@pytest.mark.parametrize("cid", UNSAFE_IDS, ids=[f"unsafe{i}" for i in range(len(UNSAFE_IDS))])
def test_unsafe_or_malformed_ids_rejected_with_400_and_not_echoed(client, cid, lookup_spy):
    r = post(client, [cid])
    assert_problem(r, 400)
    assert_not_echoed(r, cid)
    assert lookup_spy == []


INJECTION_IDS = [
    "{\"$ne\": null}", "$ne", "$gt", "{\"$gt\":\"\"}", "[$ne]=1", "a[$ne]", "__proto__", "$where: 1",
    "\x3cscript\x3ealert(1)\x3c/script\x3e", "{{7*7}}", "%s%s%s%n", "; ls", "| cat", "*", ".*", "^a$", "a|b",
    "(?i)admin", "\u0000", "NUL\x00", "\x24\x7bjndi:ldap://127.0.0.1/x\x7d", "\x60id\x60", "\x24(id)",
]


@pytest.mark.parametrize("cid", INJECTION_IDS, ids=[f"inject{i}" for i in range(len(INJECTION_IDS))])
def test_injection_style_ids_rejected_with_400_and_not_echoed(client, cid, lookup_spy):
    r = post(client, [cid])
    assert_problem(r, 400)
    assert_not_echoed(r, cid)
    assert lookup_spy == []


def test_lone_surrogate_escape_in_id_is_400_not_500(client):
    r = post_raw(client, b"{\"customerIds\": [\"ab\\ud800cd\"]}")
    assert_problem(r, 400)


def test_one_bad_id_rejects_the_whole_batch_and_nothing_is_looked_up(client, lookup_spy):
    assert_problem(post(client, ["cust-1", "cust-2", "bad id", "cust-1x"]), 400)
    assert lookup_spy == []


def test_ids_are_case_sensitive(client):
    results = post(client, ["A", "a"]).json()["results"]
    assert results[0]["preferences"]["email"] is True and results[1]["preferences"]["push_notification"] is True
    assert results[0]["preferences"] != results[1]["preferences"]


# ---- non-string IDs -------------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [123, 0, -1, 1.5, True, False, None, [], ["a"], {}, {"id": "a"}, [["a"]]])
def test_non_string_ids_rejected(client, bad, lookup_spy):
    assert_problem(post(client, [bad]), 400)
    assert_problem(post(client, ["cust-1", bad]), 400)
    assert lookup_spy == []


@pytest.mark.parametrize("raw", [
    b"{\"customerIds\": [1e999]}", b"{\"customerIds\": [123456789012345678901234567890]}",
    b"{\"customerIds\": [NaN]}", b"{\"customerIds\": [Infinity]}", b"{\"customerIds\": [-0]}",
])
def test_numeric_literals_as_ids_rejected(client, raw):
    assert_problem(post_raw(client, raw), 400)


# ---- duplicates -----------------------------------------------------------------------------------

@pytest.mark.parametrize("ids", [
    ["a", "a"], ["a", "b", "a"], ["a", " a"], ["a ", "\ta\n"], ["cust-1", "cust-2", "cust-1"],
])
def test_duplicates_rejected_including_after_trimming(client, ids, lookup_spy):
    assert_problem(post(client, ids), 400)
    assert lookup_spy == []


def test_duplicate_at_the_end_of_a_100_batch_rejected(client, lookup_spy):
    ids = [f"id{i}" for i in range(99)] + ["id0"]
    assert_problem(post(client, ids), 400)
    assert lookup_spy == []


# ---- mixed valid / missing, ordering --------------------------------------------------------------

def test_mixed_valid_and_missing_preserve_request_order(client):
    ids = ["zz-missing", "cust-2", "aa-missing", "alltrue", "cust-1", "mm-missing"]
    results = post(client, ids).json()["results"]
    assert [r["customerId"] for r in results] == ids
    assert [r["missing"] for r in results] == [True, False, True, False, False, True]


def test_order_is_not_sorted_and_is_stable_for_reversed_input(client):
    ids = ["cust-2", "cust-1", "allfalse", "alltrue"]
    assert [r["customerId"] for r in post(client, ids).json()["results"]] == ids
    rev = list(reversed(ids))
    assert [r["customerId"] for r in post(client, rev).json()["results"]] == rev


# ---- body-level structure -------------------------------------------------------------------------

@pytest.mark.parametrize("body", [
    {}, {"customerIds": None}, {"customerIds": "cust-1"}, {"customerIds": {"0": "cust-1"}}, {"customerIds": 5},
    {"customerIds": True}, {"customerids": ["cust-1"]}, {"CustomerIds": ["cust-1"]}, {"customer_ids": ["cust-1"]},
    {"ids": ["cust-1"]}, {"customerIds": ["cust-1"], "extra": 1}, {"customerIds": ["cust-1"], "customerId": "x"},
    {"customerIds": ["cust-1"], "__proto__": {"admin": True}},
], ids=lambda b: json.dumps(b)[:50])
def test_invalid_body_shapes_rejected(client, body):
    assert_problem(client.post(URL, json=body, headers=auth()), 400)


@pytest.mark.parametrize("raw", [b"[]", b"[\"cust-1\"]", b"\"cust-1\"", b"null", b"123", b"true", b"", b"   ", b"\n"])
def test_non_object_or_empty_bodies_rejected(client, raw):
    assert_problem(post_raw(client, raw), 400)


def test_extra_field_name_is_not_echoed(client):
    marker = "InjectedFieldName_7f3a"
    r = client.post(URL, json={"customerIds": ["cust-1"], marker: 1}, headers=auth())
    assert_problem(r, 400)
    assert marker not in r.text


MALFORMED = [
    b"{", b"}", b"{\"customerIds\": [\"cust-1\",]}", b"{\"customerIds\": [\"cust-1\"]} trailing",
    b"{\"customerIds\": [\"cust-1\"]}{\"customerIds\": [\"cust-2\"]}", b"{customerIds: [\"cust-1\"]}",
    b"{\"customerIds\": [\"cust-1\"", b"\xef\xbb\xbf{\"customerIds\": [\"cust-1\"]}", b"\xff\xfe\x00",
    b"{\"customerIds\": [\"\xff\xfe\"]}", b"{\"customerIds\": [\"cust-1\"], \"x\": NaN}", b"\x00\x00\x00",
    b"{\"customerIds\": [\"a\\u00zz\"]}", b"{\"customerIds\": [\"a\\q\"]}",
]


@pytest.mark.parametrize("raw", MALFORMED, ids=[f"malformed{i}" for i in range(len(MALFORMED))])
def test_malformed_json_and_encoding_is_400_never_500(client, raw):
    assert_problem(post_raw(client, raw), 400)


def test_deeply_nested_json_is_400_not_500(client):
    depth = 100_000
    assert_problem(post_raw(client, b"{\"customerIds\": " + b"[" * depth + b"]" * depth + b"}"), 400)
    assert_problem(post_raw(client, b"{\"customerIds\": [" + b"{\"a\":" * depth + b"1" + b"}" * depth + b"]}"), 400)


def test_duplicate_json_keys_do_not_cause_an_error(client):
    r = post_raw(client, b"{\"customerIds\": [\"cust-1\"], \"customerIds\": [\"cust-2\"]}")
    assert r.status_code in (200, 400)


def test_huge_garbage_body_rejected_without_server_error(client, lookup_spy):
    assert_problem(post_raw(client, b"x" * (6 * 1024 * 1024)), 400)
    assert lookup_spy == []


def test_huge_but_wellformed_body_with_too_many_ids_rejected(client, lookup_spy):
    assert_problem(post(client, [f"id{i}" for i in range(150_000)]), 400)
    assert lookup_spy == []


def test_huge_single_string_id_rejected(client):
    assert_problem(post(client, ["a" * 5_000_000]), 400)


# ---- content-type ---------------------------------------------------------------------------------

@pytest.mark.parametrize("ctype", [
    "text/plain", "application/x-www-form-urlencoded", "application/xml", "multipart/form-data; boundary=x",
    "application/json; charset=utf-16", "application/jsonx", "garbage", "", None,
])
def test_wrong_content_type_never_crashes_and_errors_are_problem_json(client, ctype):
    r = post_raw(client, b"{\"customerIds\": [\"cust-1\"]}", content_type=ctype)
    assert r.status_code in (200, 400, 415), r.text
    if r.status_code != 200:
        assert r.headers["content-type"].startswith("application/problem+json")


def test_non_json_payloads_with_non_json_content_type_rejected(client):
    for ctype, raw in (("application/x-www-form-urlencoded", b"customerIds=cust-1"), ("text/xml", b"\x3ca/\x3e"),
                       ("text/plain", b"cust-1")):
        assert_problem(post_raw(client, raw, content_type=ctype), 400)


def test_utf16_encoded_body_is_not_misread(client):
    raw = "{\"customerIds\": [\"cust-1\"]}".encode("utf-16")
    assert_problem(post_raw(client, raw, content_type="application/json; charset=utf-16"), 400)


# ---- HTTP methods and paths -----------------------------------------------------------------------

@pytest.mark.parametrize("method", ["GET", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
@pytest.mark.parametrize("authed", [True, False])
def test_non_post_methods_return_405_with_allow_post(client, method, authed):
    r = client.request(method, URL, headers=auth() if authed else {})
    assert r.status_code == 405
    assert "POST" in r.headers.get("allow", "")
    assert "results" not in r.text and "preferences" not in r.text


def test_put_patch_delete_with_body_do_not_mutate_or_read(client, snapshot):
    before = snapshot()
    for method in ("PUT", "PATCH", "DELETE"):
        r = client.request(method, URL, json={"customerIds": ["cust-1"]}, headers=auth())
        assert r.status_code == 405
    assert snapshot() == before


def test_unknown_sibling_paths_are_not_served(client):
    for path in ("/api/v1/customers/audit", "/api/v1/customers/audit/preference", "/api/v1/audit/preferences",
                 "/api/v1/customers/audit/preferences/cust-1"):
        assert client.post(path, json={"customerIds": ["cust-1"]}, headers=auth()).status_code in (404, 405)


def test_trailing_slash_variant_never_bypasses_auth(client):
    r = client.post(URL + "/", json={"customerIds": ["cust-1"]}, follow_redirects=True)
    assert r.status_code in (401, 404, 405)
    assert "results" not in r.text


def test_query_string_parameters_are_ignored(client):
    r = client.post(URL + "?customerIds=zzz&role=admin", json={"customerIds": ["cust-1"]}, headers=auth())
    assert r.status_code == 200 and [x["customerId"] for x in r.json()["results"]] == ["cust-1"]
    r = client.post(URL + "?role=admin&scope=preferences:audit", json={"customerIds": ["cust-1"]})
    assert_problem(r, 401)
