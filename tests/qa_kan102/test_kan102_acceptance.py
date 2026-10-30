"""KAN-102 acceptance-level tests, one section per acceptance criterion (AC-1..AC-7).

AC-8 (automated test coverage) is satisfied by this suite as a whole.
"""
from app.preferences.store import Preferences
from kan102_support import DROP, URL, assert_problem, auth, bearer, claims, make_token

JSON_CT = {"Content-Type": "application/json"}


def post(client, ids, headers=None):
    return client.post(URL, json={"customerIds": ids}, headers=headers if headers is not None else auth())


# ---- AC-1: valid JWT + 1..100 IDs returns email/sms/push per customer ------------------------------

def test_ac1_single_id_returns_all_three_channels(client):
    r = post(client, ["cust-1"])
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    assert r.json() == {"results": [{"customerId": "cust-1", "missing": False,
                                     "preferences": {"email": True, "sms": False, "push_notification": True}}]}


def test_ac1_exactly_100_ids_all_returned_in_order(client, seeded_store):
    ids = [f"bulk{i:03d}" for i in range(100)]
    for i, cid in enumerate(ids):
        seeded_store[cid] = Preferences(email=i % 2 == 0, sms=i % 3 == 0, push_notification=i % 5 == 0)
    r = post(client, ids)
    assert r.status_code == 200
    results = r.json()["results"]
    assert [x["customerId"] for x in results] == ids
    for i, item in enumerate(results):
        assert item["missing"] is False
        assert item["preferences"] == {"email": i % 2 == 0, "sms": i % 3 == 0, "push_notification": i % 5 == 0}


def test_ac1_all_false_preferences_are_still_reported(client):
    """A customer who opted out of everything is present (not missing) and all 3 flags are shown."""
    item = post(client, ["allfalse"]).json()["results"][0]
    assert item == {"customerId": "allfalse", "missing": False,
                    "preferences": {"email": False, "sms": False, "push_notification": False}}


def test_ac1_preference_values_are_real_booleans(client):
    for item in post(client, ["cust-1", "cust-2", "alltrue"]).json()["results"]:
        assert set(item["preferences"]) == {"email", "sms", "push_notification"}
        assert all(isinstance(v, bool) for v in item["preferences"].values())


# ---- AC-2: absent customers flagged missing; partial matches --------------------------------------

def test_ac2_partial_match_flags_only_absent_ids_and_keeps_order(client):
    r = post(client, ["ghost-1", "cust-2", "ghost-2", "cust-1"])
    assert r.status_code == 200
    assert r.json()["results"] == [
        {"customerId": "ghost-1", "missing": True},
        {"customerId": "cust-2", "missing": False,
         "preferences": {"email": False, "sms": True, "push_notification": False}},
        {"customerId": "ghost-2", "missing": True},
        {"customerId": "cust-1", "missing": False,
         "preferences": {"email": True, "sms": False, "push_notification": True}},
    ]


def test_ac2_all_missing_batch_is_200_not_404(client):
    r = post(client, ["nobody-1", "nobody-2"])
    assert r.status_code == 200
    assert r.json() == {"results": [{"customerId": "nobody-1", "missing": True},
                                    {"customerId": "nobody-2", "missing": True}]}


def test_ac2_missing_entries_carry_no_preferences_key(client):
    item = post(client, ["nobody"]).json()["results"][0]
    assert set(item) == {"customerId", "missing"} and item["missing"] is True


def test_ac2_empty_store_means_everything_is_missing(client, monkeypatch):
    """As shipped nothing writes to the store, so an unseeded lookup is always missing."""
    from app.preferences import store
    monkeypatch.setattr(store, "PREFERENCE_STORE", {})
    r = post(client, ["cust-1", "cust-2"])
    assert [x["missing"] for x in r.json()["results"]] == [True, True]


# ---- AC-3: more than 100 IDs rejected with RFC 7807, no processing --------------------------------

def test_ac3_101_ids_rejected_with_problem_json_and_no_lookup(client, lookup_spy):
    ids = [f"id{i:03d}" for i in range(101)]
    body = assert_problem(post(client, ids), 400)
    assert body["title"] == "Bad Request"
    assert lookup_spy == []


def test_ac3_100_ids_processed_but_101_is_not(client, lookup_spy):
    ids = [f"id{i:03d}" for i in range(100)]
    assert post(client, ids).status_code == 200
    assert len(lookup_spy) == 100
    lookup_spy.clear()
    assert post(client, ids + ["id100"]).status_code == 400
    assert lookup_spy == []


def test_ac3_very_large_batch_rejected_without_processing(client, lookup_spy):
    assert_problem(post(client, [f"x{i}" for i in range(5000)]), 400)
    assert lookup_spy == []


# ---- AC-4: missing or invalid JWT gives 401 + RFC 7807 --------------------------------------------

def test_ac4_no_authorization_header(client, lookup_spy):
    r = client.post(URL, json={"customerIds": ["cust-1"]})
    assert_problem(r, 401)
    assert r.headers["www-authenticate"] == "Bearer"
    assert lookup_spy == []


def test_ac4_invalid_signature(client, lookup_spy):
    r = client.post(URL, json={"customerIds": ["cust-1"]}, headers=bearer(make_token(secret="other-secret")))
    assert_problem(r, 401)
    assert r.headers["www-authenticate"] == "Bearer"
    assert lookup_spy == []


def test_ac4_expired_token(client, lookup_spy):
    r = client.post(URL, json={"customerIds": ["cust-1"]}, headers=auth(exp=1))
    assert_problem(r, 401)
    assert lookup_spy == []


def test_ac4_garbage_bearer(client):
    assert_problem(client.post(URL, json={"customerIds": ["cust-1"]}, headers=bearer("not.a.jwt")), 401)


# ---- AC-5: idempotency, read-only -------------------------------------------------------------------

def test_ac5_repeated_calls_are_byte_identical_and_store_unchanged(client, snapshot):
    before = snapshot()
    ids = ["cust-2", "ghost", "cust-1", "allfalse"]
    bodies = [post(client, ids).content for _ in range(5)]
    assert len(set(bodies)) == 1
    assert snapshot() == before
    assert "ghost" not in snapshot()  # lookups of unknown IDs must not create entries


def test_ac5_different_valid_tokens_give_identical_results(client):
    a = client.post(URL, json={"customerIds": ["cust-1", "x"]}, headers=auth(sub="one", role="admin"))
    b = client.post(URL, json={"customerIds": ["cust-1", "x"]},
                    headers=auth(sub="two", role="user", scope="preferences:audit"))
    assert a.status_code == b.status_code == 200 and a.content == b.content


def test_ac5_rejected_requests_do_not_touch_store(client, snapshot):
    before = snapshot()
    post(client, ["cust-1", "cust-1"])                       # duplicate gives 400
    post(client, ["cust-1"], headers={})                     # no auth gives 401
    post(client, ["cust-1"], headers=auth(role="user"))      # insufficient role gives 403
    assert snapshot() == before


# ---- AC-6: insufficient authorization gives 403 ---------------------------------------------------

def test_ac6_valid_token_with_wrong_role_is_403(client, lookup_spy):
    r = client.post(URL, json={"customerIds": ["cust-1"]}, headers=auth(role="viewer"))
    assert_problem(r, 403)
    assert lookup_spy == []


def test_ac6_token_with_no_role_and_no_scope_claims(client):
    r = client.post(URL, json={"customerIds": ["cust-1"]}, headers=bearer(make_token(claims(role=DROP))))
    assert_problem(r, 403)


def test_ac6_403_wins_over_400_body_errors(client, lookup_spy):
    r = client.post(URL, content=b"{not json", headers={**auth(role="viewer"), **JSON_CT})
    assert_problem(r, 403)
    assert lookup_spy == []


# ---- AC-7: malformed input gives 400 RFC 7807 ---------------------------------------------------

def test_ac7_missing_customerIds_field(client):
    assert_problem(client.post(URL, json={}, headers=auth()), 400)


def test_ac7_wrong_format_ids(client):
    for bad in (["bad id"], ["../etc/passwd"], ["-leading"], [""], ["a" * 65]):
        assert_problem(post(client, bad), 400)


def test_ac7_empty_batch(client):
    assert_problem(post(client, []), 400)


def test_ac7_malformed_json(client):
    r = client.post(URL, content=b"{\"customerIds\": [\"cust-1\"", headers={**auth(), **JSON_CT})
    assert_problem(r, 400)


def test_ac7_error_detail_names_the_field_without_echoing_input(client):
    marker = "ZZ-MARKER-ZZ"
    r = post(client, [f"{marker}!"])
    body = assert_problem(r, 400)
    assert marker not in r.text and "customerIds" in body["detail"]
