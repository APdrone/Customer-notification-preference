# Capstone Workflow

Use GitHub Copilot custom agents in `.github/agents/` as the orchestration layer for this repository.

## Rules

- Use `workflow/workflow.json` as the source of truth for stage order.
- Keep work scoped to the current stage artifact inside the active story folder.
- Stop at every `manual` gate and wait for a human decision.
- Capture the approval decision in the stage artifact before advancing.
- Do not invent missing requirements, reviewer decisions, or test evidence.
- Give every specialist subagent one matching instruction file under `.github/instructions/` and one matching skill under `.github/skills/`.
- Route code changes through Development, test generation through QA, and PR or release handoff through Deployment.

## Story selection

- Treat `stories/index.json` as the index of available stories.
- Work in one `stories/<story-id>/` folder at a time.
- Reuse the shared `.github/` agents and prompts across all stories.

## Persistent state

- Use `.github/ai-state.json` to keep compact cross-session workflow state.
- Store active story, current stage, latest approval decision, blockers, and evidence summary.
- Keep story-specific long-form content inside the relevant story folder, not in `.github/ai-state.json`.

## Stage ownership

- Requirements: `stories/<story-id>/requirements.md`
- Architecture: `stories/<story-id>/architecture.md`
- Design Review: `stories/<story-id>/design-review.md`
- Implementation Planning: `stories/<story-id>/impl-plan.md`
- Development evidence: `stories/<story-id>/implementation-notes.md`
- Review: `stories/<story-id>/review.md`
- QA verification: `stories/<story-id>/verify.md`
- Deployment handoff: `stories/<story-id>/pr-description.md`

## Specialist expectations

- Review must use the capstone checklist for correctness, security, error handling, test coverage, clarity, DRY, and dependency safety.
- QA must design and create unit tests, integration tests, and output quality checks using explicit QA principles.
- Deployment must own the final PR description sections and the release handoff needed to complete the workflow.
