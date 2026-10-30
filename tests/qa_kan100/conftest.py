"""KAN-100 QA fixtures: run the real JS export module under Node via driver.mjs."""
import json
import subprocess

import pytest

from kan100_support import DOC_PATH, DRIVER, MODULE, SCHEMA_PATH


def _run(payload):
    proc = subprocess.run(
        ["node", str(DRIVER), str(MODULE)],
        input=json.dumps(payload), capture_output=True, text=True, timeout=60, encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@pytest.fixture(scope="session")
def run_exports():
    """run_exports([case, ...]) -> list of result dicts (see driver.mjs)."""
    return lambda cases: _run({"cases": cases})


@pytest.fixture(scope="session")
def module_meta():
    return _run({"meta": True})


@pytest.fixture(scope="session")
def schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def doc_text():
    return DOC_PATH.read_text(encoding="utf-8")
