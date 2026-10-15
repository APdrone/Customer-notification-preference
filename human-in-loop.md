# Human In The Loop

This capstone setup does not allow the orchestration flow to move through major SDLC checkpoints without an explicit reviewer decision.

## Required approvals

| Gate | Reviewer focus | Expected decision |
| --- | --- | --- |
| `requirements-signoff` | Scope, assumptions, success criteria | Approve or request changes |
| `architecture-signoff` | Component boundaries, data flow, tech choices | Approve or request changes |
| `design-review-signoff` | Risks, gaps, mitigations | Approve or request changes |
| `development-signoff` | Delivered scope vs plan | Approve or request changes |
| `review-signoff` | Correctness, security, tests, clarity | Approve or request changes |

## Operating rule

The orchestrator may prepare outputs for a manual stage, but a human reviewer decides whether that stage is complete. If a gate is rejected, the next step is to revise the stage output instead of advancing the workflow.

After the final manual approval is captured, the deployment handoff and PR Merge stages continue automatically. The PR Merge stage is expected to use GitHub MCP to create the feature branch, open the pull request, and merge it into `master` without a separate human execution step.

Approvals are story-scoped. A reviewer approves `stories/<story-id>/requirements.md` or `stories/<story-id>/architecture.md`, not a shared global document.

## How to use this later

1. Choose the active story in `stories/index.json` or create a new folder from `stories/_template/`.
2. Use the corresponding agent file for the active stage.
3. Ask a human reviewer to approve the output against the gate criteria for manual gates only.
4. Capture the decision in the related story artifact before moving on.
5. Let the automatic PR Merge stage execute repository actions through GitHub MCP when the workflow reaches the end of the pipeline.
