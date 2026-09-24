---
description: "Use when editing workflow or approval configuration for the capstone orchestration setup."
name: "Workflow Config"
applyTo: "workflow/**/*.json"
---
# Workflow Config Rules

- Keep stage order aligned to the capstone brief.
- Every stage must have an explicit gate.
- Manual gates must name reviewer roles.
- Agent paths must point to workspace custom agents under `.github/agents/`.
