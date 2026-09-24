# Implementation Notes: Add Application Version Endpoint

**Story ID:** story-005-kan-6  
**Jira Issue:** [KAN-6](https://epam-team-ft5oad8w.atlassian.net/browse/KAN-6)  
**Status:** Complete  
**Created:** 2026-09-24  
**Verified:** 2026-09-24

## Scope Implemented

- Added config-backed application version source in [app/config/__init__.py](app/config/__init__.py)
- Added public `GET /version` endpoint in [app/main.py](app/main.py)
- Added verification tests in [tests/test_version_endpoint.py](tests/test_version_endpoint.py)

## Endpoint Contract

- `GET /version`
- Success: `200 OK` with JSON body such as `{"version": "1.2.3"}`
- Failure: `503 Service Unavailable` with `{"detail": "Version configuration unavailable"}` when config is missing or empty

## Verification Evidence

Command run:
```bash
python -m pytest tests/test_version_endpoint.py -v
```

Result:
- `2 passed in 0.37s`

This confirms the version endpoint works for both the configured and missing-config cases.