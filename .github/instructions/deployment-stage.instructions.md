---
description: "Use when editing deployment handoff artifacts for the Deployment Specialist subagent."
name: "Deployment Stage"
applyTo: "stories/**/pr-description.md"
---
# Deployment Stage Rules

- Treat the PR description as the deployment handoff artifact for the active story.
- Preserve only validated evidence from Development, Review, and QA.
- Capture the repository, branch, PR URL, release blockers, rollback notes, and required human signoffs explicitly.
- Include a summary of implemented changes, test evidence, known limitations, and reviewer checklist actions without inventing missing facts.
- Keep the final handoff tied to the active story only and never treat this as a release note for unrelated work.