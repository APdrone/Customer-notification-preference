---
description: "Use when editing architecture artifacts for the Architecture Specialist subagent."
name: "Architecture Stage"
applyTo: "stories/**/architecture.md"
---
# Architecture Stage Rules

- Trace every design decision back to one or more approved requirements.
- Document component boundaries, interfaces, data flow, and operational dependencies explicitly.
- Describe the main failure modes, recovery strategy, and security implications for each major component.
- Make explicit the assumptions, risks, tradeoffs, and rejected alternatives that require review.
- Keep unresolved decisions visible in the artifact so design review can decide whether to accept or reject them.
- State how the design supports observability, maintainability, and safe rollout for the active story.
- Do not hide architectural uncertainty; record it as a known design risk or open decision.