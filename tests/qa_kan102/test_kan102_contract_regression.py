"""OpenAPI contract, response-schema conformance, concurrency and regression of existing endpoints."""
import re
import threading

import pytest
from fastapi.testclient import TestClient

from app.preferences.store import Preferences
from app.server import app
from kan102_support import URL, assert_problem, auth, bearer, make_token

OPENAPI = app.openapi()


# ---- minimal JSON-Schema (2020-12 subset) validator; the jsonschema package is not installed -------

def resolve(ref):
    node = OPENAPI
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node


def validate(instance, schema, path="$"):
    """Return a list of violations. Supports ref, anyOf, type, required, properties, items, enum, pattern, min/max items."""
    errs = []
    if "$ref" in schema:
        return validate(instance, resolve(schema["$ref"]), path)
    if "anyOf" in schema:
        if not any(not validate(instance, sub, path) for sub in schema["anyOf"]):
            errs.append(f"{path}: no anyOf branch matches")
        return errs
    kind = schema.get("type")
    checks = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}
    if kind in checks:
        if not isinstance(instance, checks[kind]):
            return [f"{path}: expected {kind}, got {type(instance).__name__}"]
    elif kind == "integer":
        if isinstance(instance, bool) or not isinstance(instance, int):
            return [f"{path}: expected integer"]
    elif kind == "number":
        if isinstance(instance, bool) or not isinstance(instance, (int, float)):
            return [f"{path}: expected number"]
    if "enum" in schema and instance not in schema["enum"]:
        errs.append(f"{path}: not in enum")
    if kind == "string" and "pattern" in schema and not re.search(schema["pattern"], instance):
        errs.append(f"{path}: pattern mismatch")
    if kind == "array":
        if len(instance) < schema.get("minItems", 0) or len(instance) > schema.get("maxItems", 10 ** 9):
            errs.append(f"{path}: item count out of range")
        for i, item in enumerate(instance):
            errs += validate(item, schema.get("items", {}), f"{path}[{i}]")
    if kind == "object":
        for key in schema.get("required", []):
            if key not in instance:
                errs.append(f"{path}: missing required {key}")
        props = schema.get("properties", {})
        for key, value in instance.items():
            if key in props:
                errs += validate(value, props[key], f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: unexpected property {key}")
    return errs


def test_validator_self_check():
    schema = resolve("#/components/schemas/BulkPreferencesAuditResponse")
    assert validate({"results": [{"customerId": "a", "missing": True}]}, schema) == []
    assert validate({"results": [{"customerId": 1, "missing": True}]}, schema)
    assert validate({"results": [{"customerId": "a"}]}, schema)
    assert validate({}, schema)


# ---- OpenAPI document ---------------------------------------------------------------------------------

def test_openapi_exposes_post_only_audit_operation():
    ops = OPENAPI["paths"][URL]
    assert set(ops) == {"post"}
    assert "audit" in ops["post"]["tags"]


def test_openapi_request_schema_encodes_adr03_limits():
    schema = OPENAPI["paths"][URL]["post"]["requestBody"]["content"]["application/json"]["schema"]
    assert OPENAPI["paths"][URL]["post"]["requestBody"]["required"] is True
    ids = schema["properties"]["customerIds"]
    assert ids["minItems"] == 1 and ids["maxItems"] == 100 and ids["type"] == "array"
    assert ids["items"]["type"] == "string" and ids["items"]["pattern"] == "^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"
    assert schema["required"] == ["customerIds"] and schema["additionalProperties"] is False


def test_openapi_documents_every_status_the_endpoint_can_return():
    responses = OPENAPI["paths"][URL]["post"]["responses"]
    assert {"200", "400", "401", "403", "500"} <= set(responses)
    assert "422" not in responses  # validation errors are 400 problem documents


def test_openapi_response_schema_shape():
    schema = resolve("#/components/schemas/AuditResult")
    assert set(schema["required"]) == {"customerId", "missing"}
    assert set(resolve("#/components/schemas/Preferences")["properties"]) == {"email", "sms", "push_notification"}


def test_openapi_json_endpoint_serves_the_generated_document():
    r = TestClient(app).get("/openapi.json")
    assert r.status_code == 200 and r.json()["paths"][URL] == OPENAPI["paths"][URL]


# ---- real responses validate against the published schema ---------------------------------------------

def _200_schema():
    return OPENAPI["paths"][URL]["post"]["responses"]["200"]["content"]["application/json"]["schema"]


@pytest.mark.parametrize("ids", [["cust-1"], ["nobody"], ["cust-1", "nobody", "cust-2", "allfalse"], ["A", "a"]],
                         ids=["single", "missing", "mixed", "case"])
def test_success_responses_conform_to_openapi_schema(client, ids):
    r = client.post(URL, json={"customerIds": ids}, headers=auth())
    assert r.status_code == 200
    assert validate(r.json(), _200_schema()) == []
    assert set(r.json()) == {"results"}
    for item in r.json()["results"]:
        assert set(item) in ({"customerId", "missing"}, {"customerId", "missing", "preferences"})
        assert ("preferences" in item) is (item["missing"] is False)


def test_request_bodies_valid_per_published_schema_are_accepted_and_invalid_are_not(client):
    req = OPENAPI["paths"][URL]["post"]["requestBody"]["content"]["application/json"]["schema"]
    for body in ({"customerIds": ["x"]}, {"customerIds": ["a", "b", "c"]}):
        assert validate(body, req) == []
        assert client.post(URL, json=body, headers=auth()).status_code == 200
    for body in ({}, {"customerIds": []}, {"customerIds": [1]}, {"customerIds": ["x"], "y": 1}, {"customerIds": ["bad id"]}):
        assert validate(body, req)
        assert client.post(URL, json=body, headers=auth()).status_code == 400


def test_response_preferences_match_store_content_exactly(client, seeded_store):
    seeded_store["precise"] = Preferences(email=True, sms=True, push_notification=False)
    item = client.post(URL, json={"customerIds": ["precise"]}, headers=auth()).json()["results"][0]
    assert item["preferences"] == seeded_store["precise"].model_dump()


def test_response_does_not_alias_store_objects(client, seeded_store):
    """Mutating a previous response must not be able to change later responses (copies, not references)."""
    first = client.post(URL, json={"customerIds": ["cust-1"]}, headers=auth()).json()
    first["results"][0]["preferences"]["email"] = False
    second = client.post(URL, json={"customerIds": ["cust-1"]}, headers=auth()).json()
    assert second["results"][0]["preferences"]["email"] is True
    assert seeded_store["cust-1"].email is True


# ---- idempotency under concurrency --------------------------------------------------------------------

def test_concurrent_identical_requests_return_identical_responses(snapshot):
    before = snapshot()
    ids = ["cust-2", "ghost", "cust-1", "allfalse"]
    headers = auth()
    out, errors = [], []

    def worker():
        try:
            c = TestClient(app, raise_server_exceptions=False)
            for _ in range(10):
                out.append(c.post(URL, json={"customerIds": ids}, headers=headers).content)
        except Exception as exc:
            errors.append(repr(exc))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert len(out) == 80 and len(set(out)) == 1
    assert snapshot() == before


# ---- regression: existing forms endpoints are unaffected ----------------------------------------------

def test_forms_list_still_works_without_auth(client):
    r = client.get("/api/v1/forms")
    assert r.status_code == 200 and isinstance(r.json(), dict) and r.json()


def test_forms_detail_still_works_without_auth(client):
    r = client.get("/api/v1/forms/customer-preferences")
    assert r.status_code == 200
    body = r.json()
    assert body["formKey"] == "customer-preferences" and body["fields"]


def test_forms_error_behaviour_unchanged(client):
    assert client.get("/api/v1/forms/nope").status_code == 404
    assert client.get("/api/v1/forms/Bad_Key").status_code == 400


def test_forms_endpoints_ignore_bearer_tokens_and_remain_get_only(client):
    assert client.get("/api/v1/forms", headers=bearer("garbage")).status_code == 200
    assert client.post("/api/v1/forms", json={}, headers=auth()).status_code == 405


def test_forms_endpoints_listed_in_openapi_alongside_audit():
    assert {"/api/v1/forms", "/api/v1/forms/{form_key}", URL} <= set(OPENAPI["paths"])


def test_problem_json_is_not_applied_to_unrelated_404s(client):
    r = client.get("/api/v1/forms/nope")
    assert r.status_code == 404 and not r.headers["content-type"].startswith("application/problem+json")
    assert client.get("/does-not-exist").status_code == 404


def test_error_instance_is_the_request_path_only(client):
    r = client.post(URL + "?token=secret-looking-value&x=1", json={"customerIds": []}, headers=auth())
    body = assert_problem(r, 400)
    assert body["instance"] == URL and "secret-looking-value" not in r.text
