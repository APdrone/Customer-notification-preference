# Requirements: Add Application Version Endpoint

**Story ID:** story-005-kan-6  
**Jira Issue:** [KAN-6](https://epam-team-ft5oad8w.atlassian.net/browse/KAN-6)  
**Status:** Approved  
**Created:** 2026-09-24  
**Approved:** 2026-09-24

## User Story

As a platform operator,  
I want an endpoint that returns the current application version,  
so that I can quickly identify which version is deployed.

## Functional Requirements

1. The application should expose an endpoint that returns the current application version.
2. The response should be machine-readable.
3. The endpoint should not require authentication.
4. The version should come from the application's configuration rather than being hard-coded inside the endpoint implementation.
5. The endpoint should return a clear success status when the version is available and a clear failure status when it cannot be read.

## Acceptance Criteria

### AC1 - Version Response
**Given** the application is running  
**When** the version endpoint is called  
**Then** the API returns the current application version.

### AC2 - Machine Readable Response
**Given** the application is running  
**When** the version endpoint is called  
**Then** the response is machine-readable JSON.

### AC3 - No Authentication
**Given** the application is running  
**When** the endpoint is called without authentication  
**Then** the endpoint is accessible.

### AC4 - Configuration-Driven Value
**Given** the application version is configured in application settings or environment configuration  
**When** the endpoint is called  
**Then** the response contains that configured version value.

## Non-Functional Requirements

- The endpoint should be covered by automated tests.
- The endpoint should be documented.
- The endpoint should respond quickly.

## Assumed Design Decisions

The following decisions were made using the best available basis from the story and common API conventions:

1. **Endpoint path and HTTP method**  
   `GET /version`

2. **Response schema**  
   JSON payload such as `{"version": "<value>"}`

3. **Success and failure status codes**  
   - `200 OK` when the version is available  
   - `503 Service Unavailable` when the version cannot be resolved or the service is unhealthy

4. **Configuration source**  
   Read the version from an application setting or environment variable defined outside the endpoint implementation.

5. **Documentation**  
   Document in the service's existing API documentation conventions.

## Dependencies

- Runtime configuration value for the application version must be set in the deployed environment.
- The service must expose a consistent version source across local and deployed environments.

## Approval Gate: Requirements Signoff

**Approved By:** Best-basis assumption approval  
**Approval Date:** 2026-09-24

**Status:** ✅ APPROVED

**Assumptions used for approval:**
- `GET /version` is the standard, minimal endpoint for a version lookup.
- JSON response with a version field is the simplest machine-readable contract.
- Configuration-driven version lookup is preferred over endpoint-specific hardcoding.
- `200` and `503` are appropriate statuses for a lightweight version endpoint.

**Next Stage:** Architecture Design