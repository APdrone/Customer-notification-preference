---
description: "Use when the source story needs clarification before requirements can be drafted from Jira, Confluence, PDF, or other user-provided details."
name: "Clarify Story"
model: "gpt-4o"
argument-hint: "Story id and available source details"
---
Run this prompt after selecting the `Capstone Orchestrator` custom agent in chat.

Fetch the Jira story details through MCP when a Jira identifier is provided, then ask only the minimum clarifying questions needed to produce testable requirements.

Ask about:

- business goal
- in-scope systems
- documentation targets
- trigger event or source-of-truth fields
- approval expectations
- expected error and not-found cases

Return:

- summarized understanding of the story
- retrieved Jira fields or missing-source notes
- numbered clarification questions
- items that can be left as open questions if the user does not know the answer