# PR Description

## Summary

This PR adds a customer notification preferences API that allows an authenticated customer to retrieve and update their email, SMS, and push notification settings. The implementation enforces JWT-based authorization, persists preferences per customer, emits a preference-change event, and records audit events for each successful update.

## Changes Made

- Added the FastAPI-based customer preferences API in `app/main.py`.
- Added JWT validation via the `Authorization` header and customer-scoped access checks.
- Added in-memory per-customer persistence for the three supported channels: Email, SMS, and Push notification.
- Added the update endpoint and validation for request payloads.
- Added mock event-publisher and audit logging hooks for successful preference changes.
- Added an API test suite covering unauthenticated access, successful retrieval, successful update, and cross-customer isolation in `tests/test_preferences_api.py`.
- Added dependency definitions in `requirements.txt` for the FastAPI stack and test tooling.

## Test Evidence

- Command run: `cd "C:\Users\AmanPatwal\Downloads\AI_training\customer-notification-perference\project"; python -m pytest tests/test_preferences_api.py`
- Result: 4 tests passed
- Exit code: 0

## Known Limitations

- The implementation uses a development-oriented JWT helper and in-memory data store rather than a full production authentication or persistence stack.
- The event publisher is a lightweight mock, not a production message broker.
- The audit log is local to the development environment and is not yet integrated with a long-term enterprise audit store.

## Reviewer Checklist

- [x] Requirements were reviewed against the implemented behavior.
- [x] Security and secret-handling were checked.
- [x] Error handling for missing inputs and failures was reviewed.
- [x] Happy-path and edge-case tests were executed.
- [x] Naming and code clarity are acceptable.
- [x] Duplicate logic was identified or ruled out.
- [x] Dependency changes were reviewed for safety.

## Approval

- Status: Pending
- Reviewer:
- Notes:
