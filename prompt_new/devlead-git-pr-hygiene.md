---
name: devlead-git-pr-hygiene
description: Enforces branch naming patterns, implementation plan conventions, and single pull request deliverables using GitHub MCP tools.
---

# Dev Lead Git & PR Hygiene Standards

## Description
This skill enforces repository branch conventions, atomic commit practices, and the single Pull Request strategy for software deliverables.

## Content
When managing Git branches, implementation plans, and Pull Requests via GitHub MCP tools:

1. Branch Naming Convention:
   - Feature Branch: feature/<JIRA-EPIC-KEY> (e.g., feature/CORE-104)
   - Bugfix Branch: fix/<JIRA-STORY-KEY>

2. Implementation Plan Standards:
   - File Location: docs/implementation-plan.md
   - Required Sections:
     a. Scope Boundaries & Jira Traceability
     b. Milestones & Task Breakdown
     c. Technical Risks & Mitigation
     d. Target Testing & Rollout Strategy

3. Single PR Deliverable Governance:
   Do NOT open multiple PRs for a single epic. All deliverables must be committed on the feature branch and submitted in ONE PR:
   - Implementation plan: docs/implementation-plan.md
   - Business service logic: src/...
   - Database migrations: db/migrations/...
   - Automated tests: tests/...

4. PR Description Checklist:
   - Title: "feat: <JIRA-EPIC-KEY> - Summary of Changes"
   - Link to corresponding Jira Epic and Child Stories.
   - List of modified files with functional notes.
   - Verification commands for local build and testing.