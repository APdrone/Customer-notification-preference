# Agentic SDLC Capstone Workflow

This repository is the working framework for the capstone problem statement. The product to build is an automated documentation sync solution. GitHub Copilot customizations in this repo are used to run the SDLC around that product from requirements through deployment.

## Core idea

There are two layers in this repository:

- Shared workflow framework in `.github/`, `workflow/`, and `scripts/`
- Story-specific artifacts in `stories/<story-id>/`

The product is the automated documentation sync solution. The Copilot files in this repo are the operating framework used to define, design, build, review, QA, deploy, and later reuse that product across multiple stories.

## What each folder does

### `.github/agents/`

Contains the custom agent definitions that describe each role in the workflow.

- `orchestrator.agent.md` coordinates the current stage and story.
- `requirements.agent.md` asks clarifying questions and drafts requirements.
- `architecture.agent.md` drafts the solution architecture.
- `design-review.agent.md` captures design risks and review decisions.
- `implementation-planner.agent.md` creates the dependency-ordered implementation plan.
- `development.agent.md` is used while building the actual solution.
- `review.agent.md` performs structured review.
- `qa.agent.md` drives test design, test creation, and verification evidence.
- `deployment.agent.md` prepares the final deployment handoff for the active story.

### `.github/prompts/`

Contains reusable prompt entry points for common workflow actions.

- `start-capstone-pipeline.prompt.md` starts the pipeline from a Jira issue key.
- `resume-capstone-pipeline.prompt.md` resumes the pipeline after human feedback or approval.
- `run-capstone-stage.prompt.md` starts or continues a stage.
- `clarify-story.prompt.md` asks the minimum clarifying questions required before requirements are drafted.
- `request-approval.prompt.md` prepares the human approval request for a stage.

Use these prompts after selecting the appropriate agent manually in Copilot Chat.

### `.github/instructions/`

Contains scoped instructions that load automatically for matching files.

- `capstone-artifacts.instructions.md` applies to story artifacts.
- `*-stage.instructions.md` files give each specialist its own stage-specific guardrails.
- `workflow.instructions.md` applies to workflow configuration.

These files keep Copilot behavior consistent without repeating the same guidance in every prompt.

### `.github/hooks/`

Contains lifecycle hook configuration used to reinforce policy. In this repo, hooks are used to remind the workflow not to skip manual approval gates.

### `.github/copilot-instructions.md`

Contains repository-wide operating rules for Copilot. This is the always-on guidance that tells Copilot to:

- use `workflow/workflow.json` as the stage source of truth
- stay inside the active story folder
- stop at manual approval gates
- keep `.github/ai-state.json` compact and durable

If `agents/` defines roles, `copilot-instructions.md` defines the repo-wide rules those roles should follow.

### `.github/PULL_REQUEST_TEMPLATE.md`

Contains the PR structure expected at the end of the workflow. The story-level PR artifact in `stories/<story-id>/pr-description.md` is where the capstone content is drafted first, and this template defines the final GitHub PR sections that must be present.

Think of it this way:

- `stories/<story-id>/pr-description.md` is the working draft for one story
- `.github/PULL_REQUEST_TEMPLATE.md` is the repository-wide PR shape applied at the end

### `.github/skills/`

Contains reusable role guidance for each specialist agent. Each subagent has a matching skill with the checklist, heuristics, and quality bar for its stage.

### `.github/ai-state.json`

Stores compact cross-session workflow state, including:

- active story
- current stage
- latest approval status
- blockers
- evidence summary
- open questions

Use it as durable workflow memory, not as a place for long-form analysis.

### `workflow/`

Contains the machine-readable stage map. [workflow/workflow.json](workflow/workflow.json) defines:

- stage order
- owning agent for each stage
- story output path template for each stage
- manual or automatic approval gates
- reviewer roles for gated steps

This file is the stage router. It tells the orchestrator which agent owns which step and which story artifact should be produced next.

### `stories/`

Contains one folder per story. Each story folder owns its own requirements, architecture, design review, implementation plan, implementation notes, review, verification notes, and PR description.

- [stories/index.json](stories/index.json) tracks the active story.
- [stories/_template](stories/_template) is the starting point for new stories.
- [stories/story-001-automated-documentation-sync](stories/story-001-automated-documentation-sync) is the current active story workspace.

This is where the actual SDLC outputs live. Shared Copilot files tell the workflow how to behave, but `stories/` is where the real deliverables are written.

### `scripts/`

Contains local validation scripts. [scripts/validate-copilot-setup.ps1](scripts/validate-copilot-setup.ps1) verifies that the workflow assets and active story structure are intact.

Use scripts to validate the framework, not to replace the Copilot workflow itself.

## How the parts relate

The repository works as a chain of control and output:

1. `.github/copilot-instructions.md` sets repo-wide behavior.
2. `.github/agents/` defines the specialist roles for each capstone step.
3. `.github/prompts/` gives reusable ways to start common actions with those agents.
4. `.github/instructions/` adds file-scoped guardrails when specific artifacts are being edited.
5. `.github/hooks/` reinforces runtime policy, especially approval discipline.
6. `.github/skills/` supplies role-specific guidance for each specialist handling the solution lifecycle.
7. `workflow/workflow.json` defines the step order, owners, and outputs.
8. `stories/index.json` selects the active story.
9. `stories/<story-id>/...` stores the actual requirements, architecture, reviews, verification notes, and PR draft.
10. `.github/ai-state.json` stores the compact cross-session snapshot of progress.
11. `scripts/validate-copilot-setup.ps1` checks that the structure is still valid.

In short:

- `workflow/` decides what should happen next
- `.github/agents/` decides who should do it
- `.github/instructions/` and `.github/hooks/` constrain how it should happen
- `stories/` stores what was produced
- `.github/ai-state.json` remembers where the process currently stands

## Example: Jira ticket to PR-ready output

Assume the user gives the Jira key `DOC-123`.

### Step 1: Requirements intake

1. The user selects the `Capstone Orchestrator` agent in Copilot Chat.
2. The user runs `Start Capstone Pipeline` and provides `story-001-automated-documentation-sync DOC-123`.
3. MCP retrieves the Jira issue details using the configured Jira tools in the VS Code environment.
4. The orchestrator checks [workflow/workflow.json](workflow/workflow.json) and sees that the active stage is `requirements`.
5. The orchestrator uses [.github/agents/requirements.agent.md](.github/agents/requirements.agent.md) to drive the requirements behavior.
6. If Jira data is incomplete, [.github/prompts/clarify-story.prompt.md](.github/prompts/clarify-story.prompt.md) guides the clarification questions to the human.
7. The resulting artifact is written to [stories/story-001-automated-documentation-sync/requirements.md](stories/story-001-automated-documentation-sync/requirements.md).
8. The current workflow state is summarized in [.github/ai-state.json](.github/ai-state.json).

If clarification answers or human approval are needed, the user responds in chat and then runs `Resume Capstone Pipeline` so the workflow continues from the saved stage instead of restarting.

### Step 2: Architecture

1. The orchestrator reads [workflow/workflow.json](workflow/workflow.json) and sees the next stage is `architecture`.
2. [.github/agents/architecture.agent.md](.github/agents/architecture.agent.md) is the specialist for that step.
3. [.github/instructions/capstone-artifacts.instructions.md](.github/instructions/capstone-artifacts.instructions.md) applies when the architecture artifact is edited.
4. The architecture output is written to [stories/story-001-automated-documentation-sync/architecture.md](stories/story-001-automated-documentation-sync/architecture.md).
5. The stage pauses for `architecture-signoff` because the workflow gate is manual.

### Step 3: Design review and planning

1. [.github/agents/design-review.agent.md](.github/agents/design-review.agent.md) reviews the architecture and writes findings to [stories/story-001-automated-documentation-sync/design-review.md](stories/story-001-automated-documentation-sync/design-review.md).
2. [.github/agents/implementation-planner.agent.md](.github/agents/implementation-planner.agent.md) turns the approved design into [stories/story-001-automated-documentation-sync/impl-plan.md](stories/story-001-automated-documentation-sync/impl-plan.md).
3. `.github/hooks/manual-gates.json` reinforces that these manual review points must not be skipped.

### Step 4: Development

1. [.github/agents/development.agent.md](.github/agents/development.agent.md) is used while building the actual automated documentation sync solution.
2. [.github/instructions/development-stage.instructions.md](.github/instructions/development-stage.instructions.md) keeps implementation evidence aligned with the approved plan.
3. [.github/skills/development-specialist/SKILL.md](.github/skills/development-specialist/SKILL.md) gives the Development agent its delivery checklist and evidence rules.
4. Implementation notes and evidence are recorded in [stories/story-001-automated-documentation-sync/implementation-notes.md](stories/story-001-automated-documentation-sync/implementation-notes.md).
5. If implementation changes assumptions, story artifacts are updated and the current state is mirrored into [.github/ai-state.json](.github/ai-state.json).

### Step 5: Review and QA

1. [.github/agents/review.agent.md](.github/agents/review.agent.md) performs the capstone review checklist and records findings in [stories/story-001-automated-documentation-sync/review.md](stories/story-001-automated-documentation-sync/review.md).
2. [.github/agents/qa.agent.md](.github/agents/qa.agent.md) creates tests from QA design principles and captures unit-test evidence, integration-test evidence, output quality checks, and limitations in [stories/story-001-automated-documentation-sync/verify.md](stories/story-001-automated-documentation-sync/verify.md).
3. [.github/skills/qa-specialist/SKILL.md](.github/skills/qa-specialist/SKILL.md) defines the QA test design principles used by that stage.
4. The repo-level review expectations are also reinforced by [.github/copilot-instructions.md](.github/copilot-instructions.md).

### Step 6: Deployment handoff

1. [.github/agents/deployment.agent.md](.github/agents/deployment.agent.md) prepares [stories/story-001-automated-documentation-sync/pr-description.md](stories/story-001-automated-documentation-sync/pr-description.md).
2. [.github/skills/deployment-specialist/SKILL.md](.github/skills/deployment-specialist/SKILL.md) defines the release handoff and PR creation checklist.
3. That draft follows the structure defined by [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md): Summary, Changes Made, Test Evidence, Known Limitations, and Reviewer Checklist.
4. The workflow pauses again for the final manual sign-off before the PR is created.

## Example mapping of files during a real run

For a Jira ticket like `DOC-123`, the main files involved would be:

- control rules: [.github/copilot-instructions.md](.github/copilot-instructions.md)
- stage routing: [workflow/workflow.json](workflow/workflow.json)
- story selection: [stories/index.json](stories/index.json)
- pipeline start entrypoint: [.github/prompts/start-capstone-pipeline.prompt.md](.github/prompts/start-capstone-pipeline.prompt.md)
- pipeline resume entrypoint: [.github/prompts/resume-capstone-pipeline.prompt.md](.github/prompts/resume-capstone-pipeline.prompt.md)
- requirements role: [.github/agents/requirements.agent.md](.github/agents/requirements.agent.md)
- clarification entry point: [.github/prompts/clarify-story.prompt.md](.github/prompts/clarify-story.prompt.md)
- approval enforcement: [.github/hooks/manual-gates.json](.github/hooks/manual-gates.json)
- story output: [stories/story-001-automated-documentation-sync/requirements.md](stories/story-001-automated-documentation-sync/requirements.md)
- progress memory: [.github/ai-state.json](.github/ai-state.json)
- final PR structure: [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md)
- setup validation: [scripts/validate-copilot-setup.ps1](scripts/validate-copilot-setup.ps1)

## End-to-end flow

1. Validate the repository structure.

	```powershell
	powershell -ExecutionPolicy Bypass -File .\scripts\validate-copilot-setup.ps1
	```

2. Select the `Capstone Orchestrator` custom agent in Copilot Chat.

3. Identify the active story in [stories/index.json](stories/index.json).

4. Start the pipeline with `.github/prompts/start-capstone-pipeline.prompt.md`.
	Provide the story id and Jira issue key or identifier so the workflow fetches the source story through MCP.

5. During the requirements stage, Copilot should ask clarifying questions first if the story is incomplete.

6. Write the output into the active story folder.
	Example: [stories/story-001-automated-documentation-sync/requirements.md](stories/story-001-automated-documentation-sync/requirements.md)

7. Stop for human approval whenever the current stage has a `manual` gate in [workflow/workflow.json](workflow/workflow.json).

8. Record the decision in the story artifact and summarize the state in [.github/ai-state.json](.github/ai-state.json).

9. Move to the next stage and repeat until deployment handoff is complete.
10. Whenever the workflow pauses for approval or clarifying answers, use `.github/prompts/resume-capstone-pipeline.prompt.md` to continue from saved state.

## Human in the loop

The capstone requires explicit human review at major stage boundaries. This setup is designed to stop at those boundaries instead of silently continuing.

Manual approval gates currently exist for:

- requirements
- architecture
- design review
- implementation planning
- development
- review
- QA
- deployment

Approval expectations are documented in [human-in-loop.md](human-in-loop.md).

## Input mode

The intended source-of-truth flow is MCP-first:

- provide a Jira issue key or identifier in chat
- let the requirements workflow fetch story details through Jira MCP tools
- answer only the clarifying questions that remain after retrieval

Local documents can still be used as supplementary context, but Jira via MCP is the primary intake path for this solution.

## Multi-story usage

To add another story:

1. Copy [stories/_template](stories/_template) into a new folder such as `stories/story-002-your-story-name/`.
2. Add the story entry to [stories/index.json](stories/index.json).
3. Set `active_story` to the story you want to work on.
4. Run the same workflow without changing the shared agents, prompts, instructions, or hooks.

This keeps artifacts, approvals, and verification evidence isolated per story.

## Important operating constraints

- Do not rely on prompt frontmatter to bind directly to a custom agent in this VS Code build.
- Do not rely on custom-agent `handoffs` between subagents in this VS Code build.
- Select the agent manually, then run the prompt.
- Keep stage transitions controlled by the orchestrator logic and `workflow/workflow.json`.

## Recommended usage order

1. Clarify the story.
2. Draft requirements.
3. Approve requirements.
4. Draft architecture.
5. Review architecture.
6. Create the implementation plan.
7. Build the solution in the Development stage.
8. Review the implementation.
9. Create and run tests in the QA stage.
10. Prepare deployment and PR handoff documentation.
