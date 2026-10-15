---
name: pr-merge-specialist
description: "Use when the PR Merge Specialist needs a checklist for final pull request creation, merge execution, and evidence capture."
---

# PR Merge Specialist Skill

## Goals

- Finalize the approved work through a PR and merge as the last SDLC step.
- Preserve verified evidence without rewriting it.
- Capture blockers and exact merge outcomes.
- Use GitHub tooling directly whenever it is available in the runtime.

## Checklist

- Confirm repository and target branch.
- Ensure development, review, QA, and deployment evidence is complete.
- Create the feature branch and push the approved changes by using GitHub MCP.
- If the change set is large, push in smaller logical batches so an oversized `push_files` request does not cancel the stage.
- Create the PR for the current branch without handing the step back to the user.
- Merge into `master` according to repo policy, including auto-merge if enabled.
- Record the PR URL, merge result, and any blockers.
