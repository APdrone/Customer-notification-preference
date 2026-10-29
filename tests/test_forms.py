from typing import Optional

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.api import forms_controller
from app.forms.models import REQUIRED_INDICATOR, format_label
from app.forms.providers.pydantic_provider import build_fields
from app.forms.registry import FormDefinition, FormRegistry
from app.server import app


class Profile(BaseModel):
    full_name: str
    age: int
    nickname: Optional[str] = None
    tags: list = []


def by_key(fields):
    return {f.key: f for f in fields}


# KAN-97 AC1: required fields show an asterisk
def test_required_fields_get_asterisk():
    f = by_key(build_fields(Profile))
    assert f["full_name"].required
    assert f["full_name"].displayLabel == "Full Name *"
    assert f["age"].required and f["age"].displayLabel.endswith(REQUIRED_INDICATOR)


# KAN-97 AC2: optional fields have no asterisk
def test_optional_fields_have_no_asterisk():
    f = by_key(build_fields(Profile))
    for key in ("nickname", "tags"):
        assert not f[key].required
        assert REQUIRED_INDICATOR not in f[key].displayLabel


# KAN-98 AC2: adding a required field needs no custom logic
def test_new_required_field_is_marked_automatically():
    class Extended(Profile):
        phone: str

    assert by_key(build_fields(Extended))["phone"].displayLabel == "Phone *"


def test_type_mapping():
    f = by_key(build_fields(Profile))
    assert (f["full_name"].type, f["age"].type) == ("string", "number")
    assert (f["nickname"].type, f["tags"].type) == ("string", "array")


# KAN-97 AC3: the indicator never changes validation
def test_required_override_is_visual_only():
    f = by_key(build_fields(Profile, required_overrides=["nickname"]))
    assert f["nickname"].required
    Profile(full_name="A", age=1)  # still valid without nickname


def test_override_unknown_field_rejected():
    with pytest.raises(ValueError):
        build_fields(Profile, required_overrides=["nope"])


def test_format_label():
    assert format_label("Email", True) == "Email *"
    assert format_label("Email", False) == "Email"


client = TestClient(app)


def test_customer_preferences_endpoint():
    r = client.get("/api/v1/forms/customer-preferences")
    assert r.status_code == 200
    body = r.json()
    assert body["formKey"] == "customer-preferences"
    assert body["requiredIndicator"] == "*"
    assert [f["key"] for f in body["fields"]] == ["email", "sms", "push_notification"]
    # every Preferences field has a default, so none is required
    assert all(not f["required"] and "*" not in f["displayLabel"] for f in body["fields"])
    assert body["fields"][0]["helpText"] == "Receive notifications via email"


def test_unknown_form_404():
    assert client.get("/api/v1/forms/nope").status_code == 404


def test_endpoint_marks_required_from_registry(monkeypatch):
    reg = FormRegistry()
    reg.register(FormDefinition("profile", "Profile", Profile))
    monkeypatch.setattr(forms_controller, "registry", reg)
    fields = {f["key"]: f for f in client.get("/api/v1/forms/profile").json()["fields"]}
    assert fields["full_name"]["displayLabel"] == "Full Name *"
    assert fields["nickname"]["displayLabel"] == "Nickname"


def test_push_notification_label():
    body = client.get("/api/v1/forms/customer-preferences").json()
    assert body["fields"][2]["label"] == "Push notification"


def test_invalid_form_key_returns_400():
    assert client.get("/api/v1/forms/Bad_Key!").status_code == 400
    assert client.get("/api/v1/forms/-leading").status_code == 400


def test_list_forms():
    r = client.get("/api/v1/forms")
    assert r.status_code == 200
    assert "customer-preferences" in r.json()["forms"]
