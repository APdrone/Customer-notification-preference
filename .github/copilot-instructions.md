# Copilot Instructions

## Objective

Use this repository to drive the capstone workflow from requirements through deployment using GitHub Copilot custom agents, prompt files, instructions, hooks, and skills.

## Workflow rules

- Treat `workflow/workflow.json` as the source of truth for stage order.
- Keep each stage focused on its named output artifact in the active story folder.
- Use `stories/index.json` to identify the active story when more than one story exists.
- Use `.github/ai-state.json` for durable workflow state between sessions.
- Stop at every stage with a `manual` gate and wait for human approval.
- Do not bypass approval sections in story artifacts under `stories/<story-id>/`.
- Every specialist subagent must have a companion instruction file in `.github/instructions/` and a companion skill in `.github/skills/`.
- Development owns application changes, QA owns test creation and verification evidence, and Deployment owns PR or release handoff artifacts.
- When implementing the real solution later, preserve evidence needed by review, QA, and deployment.

## Agent usage

- Start from `.github/agents/orchestrator.agent.md` to coordinate the workflow.
- Use only the stage-specific agent that owns the current output.
- Keep edits minimal and scoped to the active phase and active story.
- Route build work to the Development agent, test design and execution to the QA agent, and final PR or release handoff to the Deployment agent.

## Setup rule

- Prefer GitHub Copilot's built-in orchestration surfaces over custom runtime code unless the future solution itself requires executable orchestration.

## State rule

- Keep `.github/ai-state.json` updated with the active story, current stage, approvals, blockers, and latest evidence summary.
- Do not store long narrative analysis in `.github/ai-state.json`; store compact, durable facts only.

## Review standard

- Evaluate correctness, security, error handling, test coverage, clarity, duplication, and dependency safety before deployment handoff.
