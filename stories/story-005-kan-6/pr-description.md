# PR Description: Add Application Version Endpoint

**Story ID:** story-005-kan-6  
**Jira Issue:** [KAN-6](https://epam-team-ft5oad8w.atlassian.net/browse/KAN-6)  
**Branch:** feature/story-005-version-endpoint  
**Status:** Ready for Review  
**Created:** 2026-09-24

---

## Summary

This PR adds a lightweight public API endpoint that returns the currently configured application version. It supports operations teams and deployment monitoring by exposing the running version without requiring authentication.

The implementation includes:
- a public `GET /version` route
- configuration-backed version lookup via `APP_VERSION`
- JSON response payload with the version string
- safe failure handling with `503 Service Unavailable` when no version is configured
- direct verification with targeted automated tests

### Acceptance Criteria Status

| Criterion | Description | Status |
|-----------|-------------|--------|
| AC1 | Returns the current application version | ✅ VERIFIED |
| AC2 | Response is machine-readable | ✅ VERIFIED |
| AC3 | Endpoint does not require authentication | ✅ VERIFIED |
| AC4 | Response contains the configured value from app configuration | ✅ VERIFIED |

---

## Changes Made

### Files Modified

1. **`app/config/__init__.py`**
   - Added `APP_VERSION` configuration value.
   - Keeps the version source centralized and external to the route logic.

2. **`app/main.py`**
   - Added public `GET /version` endpoint.
   - Returns `200 OK` with `{"version": "<value>"}` when configured.
   - Returns `503 Service Unavailable` with `{"detail": "Version configuration unavailable"}` when empty or missing.

3. **`tests/test_version_endpoint.py`**
   - Added targeted tests for success and failure conditions.

---

## Test Evidence

### Command Run
```bash
python -m pytest tests/test_version_endpoint.py -v
```

### Result
```text
tests/test_version_endpoint.py::TestVersionEndpoint::test_version_endpoint_returns_configured_version PASSED
tests/test_version_endpoint.py::TestVersionEndpoint::test_version_endpoint_returns_503_when_config_missing PASSED

2 passed in 0.37s
```

---

## Review and QA Summary

### Review Status
- Correctness: ✅ pass
- Security: ✅ pass
- Error handling: ✅ pass
- Test coverage: ✅ pass
- Maintainability: ✅ pass

### QA Status
- Verified requirement coverage for success and failure paths
- Direct evidence recorded for both route behavior and configuration-driven output

---

## Notes

- The endpoint is intentionally simple and public by design.
- The app version is expected to be set via configuration or environment variables in deployment.
- If the version is missing, the route still responds safely without crashing the app.

---

## Deployment Notes

- Repository target: `https://github.com/APdrone/Customer-notification-preference.git`
- No known blockers.
- Rollback is straightforward: remove or disable the `GET /version` route if needed; no schema migrations or data changes were introduced.