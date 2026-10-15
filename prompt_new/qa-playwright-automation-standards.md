---
name: qa-playwright-automation-standards
description: Enforces Playwright best practices, locator resilience, test case coverage matrices, and execution publishing standards.
---

# QA Playwright Test Automation Standards

## Description
This skill guides the QA Automation Assistant in generating, structuring, and verifying automated Playwright test scripts, and reporting execution results to Jira and Confluence.

## Content
When designing and verifying automated test suites in Playwright:

1. Test Design Standards:
   - File Location: tests/<feature_name>.spec.js
   - Locators: Use resilient user-facing locators (page.getByRole, page.getByTestId) over brittle CSS selectors or absolute XPaths.
   - Assertions: Always use web-first async assertions with built-in retry mechanisms (e.g., await expect(locator).toHaveText(...)).
   - State Isolation: Ensure each test runs independently without relying on state from preceding tests.

2. Required Coverage Scenarios:
   - Happy Path: Valid payload submissions verifying expected UI updates or API responses (HTTP 200).
   - Idempotent Suppression: Valid re-submission with identical data verifying no side-effects or redundant DB rows occur.
   - Validation & Error Cases: Invalid data payloads verifying HTTP 400 Bad Request and validation error messages.
   - Authorization Checks: Requests lacking credentials verifying HTTP 401/403 responses.

3. Reporting Standards:
   Publish an execution summary to Jira and Confluence containing:
   - Total Tests Executed
   - Passed Tests vs. Failed Tests
   - Execution Duration
   - Direct link to test reports or execution traces