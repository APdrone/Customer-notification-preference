---
description: "Use when editing PR merge artifacts for the PR Merge Specialist subagent."
name: "PR Merge Stage"
applyTo: "stories/**/pr-merge.md"
---
# PR Merge Stage Rules

- Treat PR creation and merge as the final SDLC stage for the active story.
- Preserve only validated evidence from Development, Review, QA, and the deployment handoff.
- Capture the repository, target branch, PR URL, merge status, and blockers explicitly.
- Keep the final merge stage tied to the active story only and never treat it as unrelated release work.
- **MANDATORY: Use GitHub MCP server tools for branch creation, push, PR creation, and merge. Do NOT execute local terminal commands (`gh`, `git push`, etc.) for remote operations.**
- Prefer smaller GitHub MCP `push_files` batches when the change set is large. If a large push is cancelled or fails before GitHub accepts it, retry with smaller story-scoped or code-scoped batches instead of treating the run as blocked.
- Do not stop at a manual handoff if the active agent can complete the repository actions itself.
- If the merge is blocked by repository settings, missing MCP tools, or permissions, record the exact blocker in `pr-merge.md` and halt. Do not invent a successful merge.
