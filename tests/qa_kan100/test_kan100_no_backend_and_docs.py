"""KAN-100 QA: no backend change (AC5), docs/design/code consistency, acceptance criteria inventory."""
import json
import re
import shutil
import subprocess

import pytest

from app.server import app

from kan100_support import KEY_ORDER, ROOT, needs_node

# Literal strings from Confluence 23855126 (Architecture Design, Error handling UX).
CONF_NOT_LOADED = "Preferences are not loaded yet. Please refresh and try again."
CONF_DOWNLOAD_FAILED = "Export failed due to a browser download error. Please try again or use another browser."
FENCE = "`" * 3


def test_no_export_route_in_app_or_openapi():
    paths = {getattr(r, "path", "") for r in app.routes}
    assert not [p for p in paths if "export" in p.lower()], paths
    assert not [p for p in app.openapi()["paths"] if "export" in p.lower()]


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_kan100_changes_since_kan97_merge_touch_no_backend_files():
    probe = subprocess.run(["git", "rev-parse", "--verify", "-q", "f4a3ac1^{commit}"], cwd=ROOT, capture_output=True)
    if probe.returncode != 0:
        pytest.skip("baseline commit f4a3ac1 not available")
    out = subprocess.run(["git", "diff", "--name-only", "f4a3ac1", "47f8dbf"], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout.split()
    assert not [f for f in out if f.startswith("app/")], out
    assert any(f.startswith("web/export/") for f in out)


def test_acceptance_criteria_inventory_is_eight_scenarios(doc_text):
    scenarios = re.findall(r"^\s*Scenario: (.+)$", doc_text, flags=re.M)
    assert len(scenarios) == 8, scenarios


@needs_node
def test_error_messages_match_confluence_and_docs(module_meta, doc_text):
    msgs = module_meta["ERROR_MESSAGES"]
    codes = module_meta["ERROR_CODES"]
    assert msgs[codes["NOT_LOADED"]] == CONF_NOT_LOADED
    assert msgs[codes["INVALID"]] == CONF_NOT_LOADED
    assert msgs[codes["DOWNLOAD_FAILED"]] == CONF_DOWNLOAD_FAILED
    assert CONF_NOT_LOADED in doc_text and CONF_DOWNLOAD_FAILED in doc_text
    for code in codes.values():
        assert "`" + code + "`" in doc_text


@needs_node
def test_documented_example_matches_real_output_shape(run_exports, doc_text):
    start = doc_text.index(FENCE + "json\n") + len(FENCE + "json\n")
    block = doc_text[start:doc_text.index(FENCE, start)]
    example = json.loads(block)
    (r,) = run_exports([{"customerId": "<customerId>", "prefs": {"email": True, "sms": False, "push_notification": True},
                         "now": "2026-10-30T00:00:00Z"}])
    real = json.loads(r["text"])
    assert list(example) == list(real) == KEY_ORDER
    assert {k: type(v) for k, v in example.items()} == {k: type(v) for k, v in real.items()}
    assert example["email"] is True and example["sms"] is False and example["push_notification"] is True


@needs_node
def test_public_api_surface(module_meta):
    for name in ("buildExportPayload", "serializePayload", "exportPreferencesJson", "canExport",
                 "ExportError", "ERROR_CODES", "ERROR_MESSAGES"):
        assert name in module_meta["exports"]


def test_demo_page_labels_stub_data_and_docs_mention_it(doc_text):
    html = (ROOT / "web" / "export" / "index.html").read_text(encoding="utf-8")
    assert "stub" in html.lower()
    assert "stub" in doc_text.lower()
