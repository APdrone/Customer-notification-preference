---
name: solution-architect-design-standards
description: Standardizes Confluence architecture pages, High-Level Design (HLD), Low-Level Design (LLD), Mermaid diagrams, and REST API specs.
---

# Solution Architecture & Design Standards

## Description
This skill provides the structure and diagram conventions required when generating architectural documentation, system designs, and wireframes in Confluence.

## Content
When generating architecture artifacts for publishing to Confluence, structure the content in the following sequence:

1. Executive Summary & Design Scope:
   - Provide 2-3 sentences summarizing the technical change.
   - List the verified Jira Epic and Story keys linked to this design.

2. Component & Flow Diagram:
   Represent microservices, caching layers, and database interactions using valid Mermaid graph syntax (graph TD).

3. Database Schema & ERD:
   Represent entity models, primary keys, relationships, and audit attributes using valid Mermaid erDiagram syntax.

4. REST API Specification:
   - Method & Route: e.g., PUT /api/v1/customers/{id}/preferences
   - Idempotency Guarantee: Specify headers and payload hashing mechanism.
   - Request & Response JSON schemas with explicit HTTP error status codes (400, 401, 404, 500).

5. Non-Functional Requirements (NFR) Checklist:
   - Performance: Latency budgets (e.g., p99 < 50ms).
   - Concurrency & Lock Suppression: Zero duplicate DB writes on replayed requests.
   - Observability: Prometheus metrics and distributed tracing spans defined.