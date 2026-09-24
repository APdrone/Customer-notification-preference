# Architecture: Add Application Version Endpoint

**Story ID:** story-005-kan-6  
**Jira Issue:** [KAN-6](https://epam-team-ft5oad8w.atlassian.net/browse/KAN-6)  
**Status:** Draft for architecture signoff  
**Created:** 2026-09-24  
**Approved Requirements:** 2026-09-24

## Overview

Implement a lightweight public version endpoint for the FastAPI application so operators can determine which application build is deployed without needing authentication. The endpoint will read the value from configuration and return it as a machine-readable JSON response. This design keeps the version source centralized and avoids hard-coding values in the route handler.

## Design Principles

1. **Traceability to requirements**: every design choice supports the approved requirements.
2. **Low coupling**: the endpoint reads version data from configuration instead of embedded business logic.
3. **Minimal surface area**: single route, simple response shape, no authentication requirement.
4. **Operational safety**: if configuration is missing or invalid, the endpoint responds with a clear server error instead of crashing.
5. **Observability**: response behavior and failure paths are explicit enough to test and monitor.

## High-Level Architecture

```text
Client / Monitoring Tool
          |
          v
FastAPI Route: GET /version
          |
          v
Version Service / Handler
          |
          v
Application Config Source
  (env var or settings object)
          |
          v
JSON Response
200 OK with {"version": "..."}
503 Service Unavailable on config/read error
```

## Key Components

### 1. Application Configuration Layer
- **Location:** existing configuration module pattern under `app/config/`
- **Responsibility:** hold the configured application version as a single source of truth
- **Implementation approach:** read from environment variables or a centralized settings object, for example `APP_VERSION` or `VERSION`
- **Failure mode:** if the variable is unset or invalid, the endpoint should return a handled failure response

### 2. Version Retrieval Service
- **Responsibility:** resolve the runtime version value from configuration and return it for the API layer
- **Behavior:** no logic beyond reading config, validating non-empty value, and returning the value to the route
- **Why this is needed:** keeps the endpoint simple and ensures version configuration is not duplicated across the codebase

### 3. Version Endpoint Handler
- **Path:** `GET /version`
- **Authentication:** none
- **Responsibility:** call the version retrieval service and format the JSON response
- **Success response:**
  ```json
  {
    "version": "1.2.3"
  }
  ```
  - HTTP status: `200 OK`
- **Failure response:**
  ```json
  {
    "detail": "Version configuration unavailable"
  }
  ```
  - HTTP status: `503 Service Unavailable`

## API Contract

### Request
```
GET /version
Host: [application-host]
Authorization: none required
```

### Success Response
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "version": "1.2.3"
}
```

### Failure Response
```http
HTTP/1.1 503 Service Unavailable
Content-Type: application/json

{
  "detail": "Version configuration unavailable"
}
```

## Technical Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Route pattern | `GET /version` | Simple, discoverable, aligns with common API conventions |
| Response format | JSON object with `version` field | Machine-readable and easy for automation to parse |
| Version source | App configuration or environment variable | Satisfies requirement to avoid hard-coded endpoint value |
| Failure handling | Return `503` and clear detail message | Explicit server-side failure without crashing the app |
| Authentication | None | Explicitly required by approved story |
| Scope | Single endpoint only | Keeps MVP focused and lower risk |

## Data Flow

1. HTTP request arrives at `GET /version`.
2. FastAPI route invokes the version retrieval logic.
3. Version logic reads the configured version from environment or application settings.
4. A validation check ensures a non-empty value is returned.
5. Route returns JSON with either the version value or a structured server error.

## Failure Modes and Recovery

### Case 1: Missing Configuration Value
- **Behavior:** route catches missing/empty config and returns 503.
- **Recovery:** set the config value in the deployment environment and retry.

### Case 2: Invalid Configuration Format
- **Behavior:** route treats invalid configuration as unavailable and returns a clear failure response.
- **Recovery:** fix configuration format and redeploy or restart the application.

### Case 3: Unexpected Runtime Error
- **Behavior:** exception is caught by route-level error handling to avoid crashing the process.
- **Recovery:** log the issue and continue serving other endpoints while config is corrected.

## Security Considerations

- The endpoint is public by design and does not expose credentials or sensitive internal data.
- The response contains only the application version and no business data.
- No write operations are performed.
- Minimal exposure risk because the response is low-sensitivity and intentionally public.

## Observability and Maintainability

- The route is easy to test using FastAPI test client calls.
- The response contract is explicit and stable for monitoring scripts or UI clients.
- The configuration-driven approach centralizes the version value, which reduces maintenance over time.
- Structured error handling keeps logs clear and helps diagnose deployment or environment issues.

## Non-Functional Requirement Alignment

| Requirement | Design Response |
|-------------|-----------------|
| Automated tests | Route and config contract can be unit-tested and integration-tested |
| Documentation | Endpoint contract can be documented in API docs and comments |
| Fast response | No external dependency calls; simple config lookup |
| Machine-readable output | JSON response |
| No authentication | Public route with no auth gate |

## Requirements Traceability

| Requirement | Design Element |
|-------------|----------------|
| Expose endpoint returning current application version | `GET /version` route |
| Machine-readable response | JSON object with `version` field |
| No authentication | Public route without auth dependency |
| Version sourced from configuration | Config/env-driven retrieval service |
| Clear failure response | `503 Service Unavailable` with descriptive detail |

## Risks and Tradeoffs

### Risk: Configuration drift across environments
- **Impact:** deployed environments may return different versions or missing values.
- **Mitigation:** enforce a single env var or settings contract and validate config on startup.

### Tradeoff: Simpler JSON contract vs richer metadata
- **Chosen approach:** keep only the version value to minimize complexity and avoid unnecessary API surface.
- **Rejected alternative:** returning additional metadata such as build ID, timestamp, or environment in the same response; this would broaden scope without business need.

## Open Decisions for Design Review

1. Should the application version be sourced from a single environment variable such as `APP_VERSION` or from a config object used throughout the app?
2. Should a startup validation log warning be emitted when the version setting is missing or empty?
3. Should the failure detail message be user-facing and generic, or should it include internal deployment metadata in logs only?

---

## Approval Gate: Architecture Signoff

**Status:** Pending approval

**Review Checklist:**
- [x] Requirements traceability is explicit
- [x] Endpoint contract is clear and minimal
- [x] Configuration-driven source is defined
- [x] Failure handling is documented
- [x] Security and observability considerations are covered
- [x] Risks and open decisions are visible

**Next Stage:** Await architecture approval before moving to design review or implementation.