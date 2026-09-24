---
description: "Use when a stage artifact is ready for human review and the approval decision must be captured before advancing."
name: "Request Stage Approval"
model: "gpt-4o"
argument-hint: "Story artifact path and gate id"
---
Review the specified artifact against its stage goals and the gate definition in `workflow/workflow.json`.

Return:

- Gate id
- Reviewer checklist
- Approval status placeholder
- Follow-up questions for the human reviewer
