---
description: "Use when starting or continuing a capstone SDLC stage with the orchestrator agent."
name: "Run Capstone Stage"
model: "gpt-4o"
argument-hint: "Story id, stage, source artifact, and requested outcome"
---
Run this prompt after selecting the `Capstone Orchestrator` custom agent in chat.

Use `stories/index.json` and `workflow/workflow.json` to identify the active story and stage, delegate to the correct specialist agent, and stop at the next manual approval gate.

If the source is a Jira item, use the Jira identifier provided by the user to fetch the source details through MCP before drafting or reviewing artifacts.

If the active stage is requirements, ask clarifying questions first when the story details are not sufficient to write testable requirements.

Return:

- Active story folder
- Active stage
- Target artifact
- Assigned specialist
- Required human approval before advancing

