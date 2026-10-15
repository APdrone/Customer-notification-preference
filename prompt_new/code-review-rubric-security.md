---
name: code-review-rubric-security
description: Provides guidelines for PR code inspection, security audits (OWASP Top 10), idempotency checks, and line-level comment formatting.
---

# Code Review & Security Audit Rubric

## Description
This skill instructs the Code Reviewer Assistant on conducting automated pull request code reviews, identifying security flaws, and posting actionable comments directly to Git.

## Content
When reviewing pull request diffs using get_pr_changes:

1. Review Categories:
   - Security (OWASP Top 10): Inspect for SQL injection vulnerabilities, untrusted parameter passing, secret/token leakage, and missing authentication/authorization checks.
   - Idempotency & Data Integrity: Confirm payload comparison logic prevents unnecessary database writes or duplicate event emissions.
   - Code Maintainability: Evaluate error handling, logging hygiene, and modular design.
   - Test Coverage: Check that automated test specs cover positive, negative, and edge cases.

2. Comment Formatting Standard:
   Every inline comment created with create_pr_change_comment must follow this template:
   - Severity: [Critical] | [Major] | [Minor] | [Nit]
   - Issue: Precise explanation of the problem or vulnerability.
   - Remediation: Concrete code snippet or exact suggestion to resolve the issue.

3. Final Review Output:
   - Group findings by severity (Critical, Major, Minor).
   - If Critical findings exist, explicitly set has_critical_findings: true to block merge authorization.