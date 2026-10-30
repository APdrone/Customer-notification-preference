"""KAN-100 QA: the claim that the export schema matches the backend Preferences model."""
import json

import pytest

from app.forms.registry import Preferences

from kan100_support import KEY_ORDER, needs_node

PREF_KEYS = ["email", "sms", "push_notification"]


def test_schema_preference_properties_equal_model_fields(schema):
    pref_props = {k: v for k, v in schema["properties"].items() if k not in ("customerId", "exportedAt")}
    assert set(pref_props) == set(Preferences.model_fields)
    for name, sub in pref_props.items():
        assert sub == {"type": "boolean"}, name
        assert Preferences.model_fields[name].annotation is bool


def test_schema_adds_exactly_customer_id_and_exported_at(schema):
    assert set(schema["properties"]) - set(Preferences.model_fields) == {"customerId", "exportedAt"}
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["additionalProperties"] is False
    assert list(schema["properties"]) == KEY_ORDER


def test_schema_declares_draft_2020_12_and_is_json_serialisable(schema):
    assert schema["$schema"].endswith("2020-12/schema")
    json.dumps(schema)


@needs_node
def test_module_preference_keys_equal_model_fields(module_meta):
    assert module_meta["PREFERENCE_KEYS"] == PREF_KEYS
    assert set(module_meta["PREFERENCE_KEYS"]) == set(Preferences.model_fields)
    assert module_meta["EXPORT_FILENAME"] == "notification-preferences.json"


@needs_node
@pytest.mark.parametrize("values", [(True, True, True), (False, False, False), (True, False, True), (False, True, False)])
def test_model_dump_feeds_export_and_export_validates_back_as_model(run_exports, values):
    """Model to export to Preferences round trip keeps every value (strict bool typing)."""
    model = Preferences(**dict(zip(PREF_KEYS, values)))
    (r,) = run_exports([{"customerId": "c1", "prefs": model.model_dump()}])
    data = json.loads(r["text"])
    back = Preferences.model_validate({k: data[k] for k in PREF_KEYS}, strict=True)
    assert back == model


@needs_node
def test_model_defaults_all_false_are_exportable(run_exports):
    (r,) = run_exports([{"customerId": "c1", "prefs": Preferences().model_dump()}])
    data = json.loads(r["text"])
    assert [data[k] for k in PREF_KEYS] == [False, False, False]


@needs_node
def test_model_dump_with_extra_fields_does_not_leak(run_exports):
    class Extended(Preferences):
        token: str = "SECRET"

    (r,) = run_exports([{"customerId": "c1", "prefs": Extended().model_dump()}])
    assert "SECRET" not in r["text"] and "token" not in r["text"]
