# Implementation Plan: Add Application Version Endpoint

**Story ID:** story-005-kan-6  
**Jira Issue:** [KAN-6](https://epam-team-ft5oad8w.atlassian.net/browse/KAN-6)  
**Status:** Approved  
**Created:** 2026-09-24  
**Approved:** 2026-09-24  
**Target Completion:** 1 implementation session

---

## Overview

Implement the public application version endpoint using the already approved requirements and architecture. The work is intentionally compact: add a route, resolve the version value from configuration, return a JSON payload, and validate the behavior with focused tests.

---

## Task Breakdown

### Task 1: Configure Version Source (15 minutes) ⭐ FOUNDATION
**Dependency:** None  
**Blockers:** None

**Objective:** Define the single source of truth for the application version.

**Description:**
Add a configuration value for the app version in the existing config pattern so the endpoint reads from configuration rather than hardcoded logic.

**Implementation Details:**
1. Add a config value such as `APP_VERSION` or `APPLICATION_VERSION` in the application settings/env pattern.
2. Ensure the value is read from environment or a config object in the same style as the existing JWT settings.
3. Keep the configuration accessible to the route as a single source of truth.
4. Validate that empty or missing values are treated as unavailable rather than quietly hidden.

**Acceptance Criteria:**
- [ ] A single configuration value exists for the application version.
- [ ] The route does not hardcode the version value.
- [ ] Missing or empty config is detected as a failure condition.

**Files to Create/Modify:**
- Modify: `app/config/__init__.py` or equivalent config module
- Modify: environment setup or app settings if needed

**Effort:** 15 minutes

---

### Task 2: Implement Version Retrieval Logic (20 minutes) ⭐ CORE
**Dependency:** Task 1  
**Blockers:** None

**Objective:** Create a minimal retrieval function that resolves the configured version value.

**Description:**
Introduce a small helper or service in the app that reads the configured version and returns it in a way the route can consume safely.

**Implementation Details:**
1. Add a small function such as `get_application_version()`.
2. Read the config value.
3. If the value is empty or invalid, raise or return a failure indicator.
4. Keep the logic intentionally small and free of business logic beyond reading configuration.

**Acceptance Criteria:**
- [ ] Returns the configured version string when available.
- [ ] Returns failure signal when version is missing or empty.
- [ ] No hardcoded value in the route logic.

**Files to Create/Modify:**
- Create or modify: configuration or version helper module
- Modify: `app/main.py` if needed for integration

**Effort:** 20 minutes

---

### Task 3: Add Public Version Endpoint (20 minutes) ⭐ API
**Dependency:** Task 2  
**Blockers:** None

**Objective:** Expose `GET /version` as a public route.

**Description:**
Add the FastAPI route and its response contract. The route should return JSON with the configured version or a clear failure response if the value cannot be resolved.

**Implementation Details:**
1. Add route: `GET /version`
2. Call the retrieval function.
3. On success: `200 OK` with JSON body such as `{"version": "1.2.3"}`
4. On failure: `503 Service Unavailable` with a JSON detail payload
5. No authentication required.

**Acceptance Criteria:**
- [ ] GET /version is publicly accessible.
- [ ] Response is valid JSON.
- [ ] Success case returns HTTP 200 and version payload.
- [ ] Failure case returns HTTP 503 and explicit detail.

**Files to Create/Modify:**
- Modify: `app/main.py`

**Effort:** 20 minutes

---

### Task 4: Add Unit Tests (25 minutes) ⭐ QUALITY
**Dependency:** Tasks 1-3  
**Blockers:** None

**Objective:** Verify route logic and configuration-driven behavior.

**Description:**
Write unit tests that confirm the version resolution and response contract behave correctly under both success and failure conditions.

**Test Cases:**
1. Returns configured version when environment/config value is set.
2. Returns failure when the version value is missing or empty.
3. Route returns `200` with JSON payload for success.
4. Route returns `503` with detail payload when config is unavailable.
5. No auth requirement is enforced by the endpoint.

**Coverage Target:** > 85% for the version endpoint and config helper logic.

**Acceptance Criteria:**
- [ ] Unit tests pass.
- [ ] Failure paths are tested.
- [ ] Route response contract is verified.

**Files to Create/Modify:**
- Create: `tests/test_version_endpoint.py`

**Effort:** 25 minutes

---

### Task 5: Validate and Capture Evidence (15 minutes) ⭐ VERIFICATION
**Dependency:** Task 4  
**Blockers:** None

**Objective:** Run the focused validation needed before handoff to the next stage.

**Description:**
Run the relevant test subset and record concrete evidence that the endpoint works and the contract matches the approved requirements.

**Implementation Details:**
1. Run pytest for the new version endpoint tests.
2. Confirm passing evidence includes HTTP status checks and JSON payload validation.
3. Capture output for the QA and review handoff.

**Acceptance Criteria:**
- [ ] Targeted tests pass.
- [ ] Explicit evidence is recorded for the next stage.
- [ ] No blockers remain for the story.

**Files to Create/Modify:**
- Update: implementation notes and test evidence files as needed

**Effort:** 15 minutes

---

## Development Handoff

**Development Owner:** implement route and config integration in the app code  
**Review Owner:** verify correctness, error handling, and API contract  
**QA Owner:** execute tests and capture test evidence  
**Deployment Owner:** final release notes and PR packaging after QA approval

---

## Verification Strategy

- Unit tests validate config-driven version resolution and route contract.
- Integration-style route checks confirm HTTP response semantics.
- QA evidence should include pass/fail counts and response validation results.

---

## Risks and Blockers

- Missing version configuration in deployment environment.
- Endpoint may be misconfigured if multiple sources define the app version differently.
- Unauthorized assumptions about the exact config variable name should be clarified before implementation if not already standardized.

---

## Completion Gate

The story is ready to proceed to development when:
- [ ] config source is in place
- [ ] route contract is implemented
- [ ] tests pass
- [ ] evidence is captured for the next stage