---
description: "Use when starting the capstone pipeline from a Jira issue key so Copilot fetches the story through MCP and begins requirements processing."
name: "Start Capstone Pipeline"
model: "gpt-4o"
argument-hint: "Story id and Jira issue key"
---
Run this prompt after selecting the `Capstone Orchestrator` custom agent in chat.

Start the capstone pipeline for the provided story id and Jira issue key.

Required behavior:

- read `stories/index.json` and `workflow/workflow.json`
- set the active stage to `requirements` if the story is new or not yet approved for requirements
- fetch the Jira issue through MCP using the provided key
- summarize the retrieved story details
- ask only the minimum clarifying questions needed to write testable requirements
- wait for human answers before drafting if clarification is still needed
- write or update `stories/<story-id>/requirements.md`
- update `.github/ai-state.json` with the active story, current stage, blockers, and latest approval status
- stop at the requirements approval gate and ask for approval instead of continuing automatically

Return:

- active story folder
- Jira issue key used
- retrieved source summary
- clarification questions if any
- next artifact being updated
- next human action required
