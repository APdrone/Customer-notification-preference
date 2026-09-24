---
description: "Use when resuming the capstone pipeline after human feedback, approval, or clarification answers were provided."
name: "Resume Capstone Pipeline"
model: "gpt-4o"
argument-hint: "Story id and new human input"
---
Run this prompt after selecting the `Capstone Orchestrator` custom agent in chat.

Resume the capstone pipeline for the provided story id.

Required behavior:

- read `.github/ai-state.json` to determine the current stage, latest approval status, blockers, and pending questions
- read `workflow/workflow.json` and the active story artifacts
- apply any new human feedback, approval, or clarification supplied in the current prompt
- continue from the current stage only when the blocking human input has been resolved
- stop again if another manual gate is reached or more clarification is needed

Return:

- active story folder
- current stage resumed
- human input consumed
- artifact updated
- next human action required, if any
