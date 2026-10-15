---
name: ba-invest-gherkin-standards
description: Enforces INVEST criteria, standard Jira ticket structure, and Gherkin BDD acceptance criteria syntax for user stories.
---

# INVEST & Gherkin Backlog Standards

## Description
This skill guides the Business Analyst Assistant to break requirements and epics into INVEST-compliant Jira user stories with standardized Gherkin acceptance criteria.

## Content
When creating or refining Jira user stories and epics, apply the following standards:

1. Jira Story Title Standard:
   Format: [Domain/Component] Verb + Target + Context
   Example: [Preferences] Suppress audit log writes on identical updates

2. User Story Narrative Format:
   - As a <role / consuming service>
   - I want to <capability / action>
   - So that <business value / performance outcome>

3. Acceptance Criteria (Gherkin BDD Syntax):
   Every story must contain at least one happy path and one negative/idempotency scenario:

   Scenario: Successful update with modified payload
     Given the user profile exists with active notification settings
     When a PUT request is received with updated email notification flags
     Then the service should update the record in the database
     And return HTTP status 200 OK with the updated payload

   Scenario: Idempotent no-op execution with identical payload
     Given the stored preferences match the incoming payload exactly
     When a PUT request is received
     Then the service should return HTTP status 200 OK
     And suppress all database UPDATE triggers and event bus emissions

4. Definition of Ready (DoR) Checklist:
   - Story adheres strictly to INVEST (Independent, Negotiable, Valuable, Estimable, Small, Testable).
   - Real Jira keys only; placeholder keys (e.g., KAN-xxx) are strictly forbidden.
   - Target repository and Confluence documentation spaces are explicitly identified.