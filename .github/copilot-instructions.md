# Copilot Instructions

## Objective

Use this repository to drive the capstone workflow from requirements through deployment using GitHub Copilot custom agents, instructions, hooks, and skills.

## Source-of-truth rules

- Treat `workflow/workflow.json` as the primary source of stage order and gate requirements.
- Treat `stories/index.json` as the source of available stories and the current active story when more than one exists.
- Treat the active story artifact in `stories/<story-id>/` as the working output for the current stage.
- Treat `.github/ai-state.json` as compact workflow state only: current stage, active story, blockers, approvals, evidence summary, and repository/PR references.

## Workflow rules

- Keep every stage scoped to its named artifact and do not let one stage write another stage's artifact.
- Stop at every manual gate and wait for explicit human approval before advancing.
- The QA stage is automatic in the workflow definition, but it must still produce evidence before deployment proceeds.
- Do not bypass approval sections in story artifacts under `stories/<story-id>/`.
- Every specialist subagent must have a matching instruction file in `.github/instructions/` and a matching skill in `.github/skills/`.
- Development owns application changes; QA owns test design and evidence; Deployment owns final PR and release handoff.
- Preserve evidence needed by Review, QA, and Deployment without inventing results or outcomes.

## Source story rules

- Prefer Jira or Confluence data via Atlassian MCP when available.
- Use local repo files as a fallback only when MCP is unavailable or the source is already stored locally.
- Do not treat pasted Jira summaries as the primary source when MCP data exists.
- If the source story is incomplete, ask the minimum clarifying questions needed before drafting the requirements artifact.
- Capture unresolved questions explicitly rather than guessing.

## Agent usage

- Start from `.github/agents/orchestrator.agent.md` to coordinate the workflow.
- Use only the stage-specific agent that owns the current output.
- Keep edits minimal and scoped to the current story and current stage.
- Route implementation work to the Development agent, test design and execution to the QA agent, and final PR or release handoff to the Deployment agent.

## State rule

- Update `.github/ai-state.json` with the active story, current stage, current gate status, blockers, and latest evidence summary.
- Keep the state compact and durable; do not store long narrative analysis in it.

## Review and acceptance standard

- Evaluate correctness, security, error handling, test coverage, clarity, duplication, and dependency safety before deployment handoff.
- Require concrete evidence for every claim in review and QA outputs.
- Treat missing evidence as a blocker, not an assumption.
