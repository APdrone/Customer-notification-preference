"""Contract tests for the KAN-100 client-side preferences export.

The export itself runs in the browser (web/export/exportPreferences.js). These
tests pin the file contract (JSON Schema), keep it in sync with the backend
``Preferences`` model, and check that no server endpoint was added.

They need no extra packages: a tiny validator covers the schema keywords used.
If ``jsonschema`` happens to be installed, it is used as an extra cross-check.
"""
import copy
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app.forms.registry import Preferences
from app.server import app

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "docs" / "schemas" / "notification-preferences-export.schema.json"
MODULE_PATH = ROOT / "web" / "export" / "exportPreferences.js"

SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

VALID = {
    "customerId": "cust-123",
    "email": True,
    "sms": False,
    "push_notification": True,
    "exportedAt": "2026-10-30T00:00:00Z",
}


def validate(instance, schema=SCHEMA):
    """Return a list of violations (supports type/required/properties/
    additionalProperties/minLength/pattern, the subset the schema uses)."""
    errors = []
    if schema.get("type") == "object":
        if not isinstance(instance, dict):
            return ["not an object"]
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"missing {key}")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            errors += [f"unexpected {k}" for k in instance if k not in props]
        for key, sub in props.items():
            if key in instance:
                errors += [f"{key}: {e}" for e in validate(instance[key], sub)]
    elif schema.get("type") == "boolean":
        if not isinstance(instance, bool):
            errors.append("not a boolean")
    elif schema.get("type") == "string":
        if not isinstance(instance, str):
            return ["not a string"]
        if len(instance) < schema.get("minLength", 0):
            errors.append("too short")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append("pattern mismatch")
    return errors


def test_valid_payload_matches_schema():
    assert validate(VALID) == []


def test_fractional_seconds_timestamp_is_valid():
    assert validate({**VALID, "exportedAt": "2026-10-30T12:34:56.789Z"}) == []


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.pop("customerId"),
        lambda d: d.pop("exportedAt"),
        lambda d: d.pop("push_notification"),
        lambda d: d.update(token="abc"),
        lambda d: d.update(jwt="abc"),
        lambda d: d.update(email="true"),
        lambda d: d.update(sms=1),
        lambda d: d.update(customerId=""),
        lambda d: d.update(customerId=123),
        lambda d: d.update(exportedAt="2026-10-30T00:00:00+02:00"),
        lambda d: d.update(exportedAt="2026-10-30"),
        lambda d: d.update(exportedAt="not-a-date"),
    ],
)
def test_invalid_payloads_are_rejected(mutate):
    bad = copy.deepcopy(VALID)
    mutate(bad)
    assert validate(bad) != []


def test_schema_is_valid_with_jsonschema_if_available():
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.Draft202012Validator.check_schema(SCHEMA)
    jsonschema.Draft202012Validator(SCHEMA).validate(VALID)


def test_preference_keys_match_backend_model():
    """Drift guard: export preference keys == Preferences model fields."""
    preference_keys = set(SCHEMA["properties"]) - {"customerId", "exportedAt"}
    assert preference_keys == set(Preferences.model_fields)
    assert all(SCHEMA["properties"][k]["type"] == "boolean" for k in preference_keys)
    assert set(SCHEMA["required"]) == set(SCHEMA["properties"])


def test_export_filename_is_fixed_constant():
    source = MODULE_PATH.read_text(encoding="utf-8")
    match = re.search(r'EXPORT_FILENAME\s*=\s*"([^"]+)"', source)
    assert match and match.group(1) == "notification-preferences.json"


def test_module_makes_no_network_calls_or_token_reads():
    source = MODULE_PATH.read_text(encoding="utf-8")
    for forbidden in ("fetch(", "XMLHttpRequest", "sendBeacon", "localStorage", "sessionStorage", "document.cookie"):
        assert forbidden not in source


def test_no_export_endpoint_added_to_backend():
    paths = [getattr(r, "path", "") for r in app.routes]
    assert not [p for p in paths if "export" in p.lower()]


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_real_module_output_conforms_to_schema():
    """Run the actual JS module under Node and validate what it produces."""
    script = (
        "import { buildExportPayload } from "
        f"{MODULE_PATH.as_uri()!r};"
        "const p = buildExportPayload('cust-9', {email:true,sms:false,push_notification:true,token:'x'});"
        "console.log(JSON.stringify(p));"
    )
    out = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True, text=True, check=True, timeout=30,
    ).stdout
    payload = json.loads(out)
    assert validate(payload) == []
    assert payload["customerId"] == "cust-9"
    assert "token" not in payload
