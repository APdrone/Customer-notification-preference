"""KAN-100 QA: files produced by the REAL JS module conform to the documented schema.

Covers AC3/AC4/AC6: exact keys + types, UTC ISO-8601 exportedAt, no extra or
sensitive properties, UTF-8 / LF / trailing newline, fixed filename and MIME type.
"""
import json
import re
from datetime import datetime, timezone

import pytest

from kan100_support import KEY_ORDER, needs_node

pytestmark = needs_node

PREFS = {"email": True, "sms": False, "push_notification": True}


def schema_errors(instance, schema):
    """Strict mini-validator for the keywords used by the schema (independent of the dev tests)."""
    errs = []
    if not isinstance(instance, dict):
        return ["not an object"]
    props = schema["properties"]
    errs += [f"missing {k}" for k in schema["required"] if k not in instance]
    if schema.get("additionalProperties") is False:
        errs += [f"unexpected {k}" for k in instance if k not in props]
    for k, sub in props.items():
        if k not in instance:
            continue
        v = instance[k]
        if sub["type"] == "boolean" and not isinstance(v, bool):
            errs.append(f"{k} not boolean")
        if sub["type"] == "string":
            if not isinstance(v, str):
                errs.append(f"{k} not string")
                continue
            if len(v) < sub.get("minLength", 0):
                errs.append(f"{k} too short")
            if "pattern" in sub and not re.search(sub["pattern"], v):
                errs.append(f"{k} pattern")
            if sub.get("format") == "date-time":
                try:
                    datetime.fromisoformat(v.replace("Z", "+00:00"))
                except ValueError:
                    errs.append(f"{k} not a real date-time")
    return errs


def _case(cid="cust-1", prefs=PREFS, now="2026-10-30T10:11:12.345Z", **kw):
    return {"customerId": cid, "prefs": prefs, "now": now, **kw}


def test_exported_file_matches_schema_and_values(run_exports, schema):
    (r,) = run_exports([_case("cust-42")])
    assert r["ok"], r
    data = json.loads(r["text"])
    assert schema_errors(data, schema) == []
    assert list(data) == KEY_ORDER
    assert data["customerId"] == "cust-42"
    assert data["email"] is True and data["sms"] is False and data["push_notification"] is True


def test_filename_and_mime_type(run_exports):
    (r,) = run_exports([_case()])
    assert r["filename"] == "notification-preferences.json"
    assert r["mime"] == "application/json"


def test_every_boolean_combination_roundtrips(run_exports, schema):
    combos = [(e, s, p) for e in (True, False) for s in (True, False) for p in (True, False)]
    results = run_exports([_case(prefs={"email": e, "sms": s, "push_notification": p}) for e, s, p in combos])
    for (e, s, p), r in zip(combos, results):
        data = json.loads(r["text"])
        assert schema_errors(data, schema) == []
        assert (data["email"], data["sms"], data["push_notification"]) == (e, s, p)


def test_exported_at_is_utc_iso8601_and_matches_clock(run_exports):
    results = run_exports([
        _case(now="2026-10-30T10:11:12.345Z"),
        _case(now="2026-10-30T23:30:00+05:30"),   # non-UTC input instant must be normalised
        _case(now="2026-12-31T23:59:59.999Z"),
    ])
    stamps = [json.loads(r["text"])["exportedAt"] for r in results]
    assert stamps == ["2026-10-30T10:11:12.345Z", "2026-10-30T18:00:00.000Z", "2026-12-31T23:59:59.999Z"]
    for s in stamps:
        parsed = datetime.fromisoformat(s.replace("Z", "+00:00"))
        assert parsed.utcoffset() == timezone.utc.utcoffset(None)


def test_exported_at_differs_between_exports(run_exports):
    a, b = run_exports([_case(now="2026-10-30T10:00:00Z"), _case(now="2026-10-30T10:00:01Z")])
    assert json.loads(a["text"])["exportedAt"] != json.loads(b["text"])["exportedAt"]


def test_sensitive_and_extra_properties_are_dropped(run_exports, schema):
    hostile = {**PREFS, "token": "SECRET", "password": "SECRET", "jwt": "SECRET", "role": "admin",
               "nested": {"token": "SECRET"}, "customerId": "evil", "exportedAt": "1970-01-01T00:00:00Z"}
    (r,) = run_exports([_case("real", prefs=hostile)])
    assert "SECRET" not in r["text"] and "evil" not in r["text"] and "1970" not in r["text"]
    assert schema_errors(json.loads(r["text"]), schema) == []


def test_file_format_is_pretty_utf8_lf_with_trailing_newline(run_exports):
    (r,) = run_exports([_case("日本語-ü")])
    text = r["text"]
    assert text.endswith("}\n") and "\r" not in text
    assert text == json.dumps(json.loads(text), indent=2, ensure_ascii=False) + "\n"
    assert not text.startswith("﻿")


@pytest.mark.parametrize("cid", ["  padded  ", "q\"uote", "line\nbreak", "</script>", "a\b", "x" * 5000, "\U0001F600"])
def test_unusual_customer_ids_survive_roundtrip(run_exports, schema, cid):
    (r,) = run_exports([_case(cid)])
    assert r["ok"]
    data = json.loads(r["text"])
    assert data["customerId"] == cid
    assert schema_errors(data, schema) == []
    assert r["filename"] == "notification-preferences.json"


@pytest.mark.parametrize(
    "case",
    [
        {"customerId": "", "prefs": PREFS},
        {"customerId": "   ", "prefs": PREFS},
        {"customerId": None, "prefs": PREFS},
        {"customerId": 123, "prefs": PREFS},
        {"customerId": "c", "prefs": None},
        {"customerId": "c", "hasPrefs": False},
        {"customerId": "c", "prefs": {}},
        {"customerId": "c", "prefs": {"email": "true", "sms": False, "push_notification": True}},
        {"customerId": "c", "prefs": {"email": 1, "sms": 0, "push_notification": 1}},
        {"customerId": "c", "prefs": {"email": True, "sms": False}},
        {"customerId": "c", "prefs": [True, False, True]},
    ],
)
def test_invalid_input_produces_no_file(run_exports, case):
    (r,) = run_exports([case])
    assert r["ok"] is False
    assert r["name"] == "ExportError"
    assert r["code"] in {"PREFERENCES_NOT_LOADED", "PREFERENCES_INVALID"}
    assert r["message"] == "Preferences are not loaded yet. Please refresh and try again."
    assert "text" not in r
