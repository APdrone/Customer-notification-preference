# Architecture

## Context

This story implements a customer-facing API for managing notification preferences. The approved requirements define a fixed schema with three supported channels: Email, SMS, and Push notification. The solution must support retrieval and update operations for an authenticated customer, persist preferences, publish preference-change events, and maintain audit records. Security is enforced with JWT-based authentication and authorization retrieved from the Authorization header, and API contracts use JSON plus RFC 7807 problem-detail error responses.

## Proposed Components

- Customer API Layer: Exposes endpoints to read and update notification preferences for the authenticated customer.
- Authentication/Authorization Middleware: Verifies JWT tokens from the Authorization header and enforces customer-scoped access.
- Preference Service: Validates input, loads the current customer preference set, and applies update logic.
- Persistence Layer: Stores customer preferences in a lightweight local repository for development, such as an in-memory store or mock database table.
- Event Publisher: Emits a preference-change event when an update succeeds using a lightweight mock publisher that logs to console or an internal bus array.
- Audit Logger: Writes immutable or append-only audit records for each successful update to a local log file or mock database table.
- API Documentation: Describes request/response schemas and standard problem-detail error responses for consumers.

## Data Flow

1. A customer sends a JWT in the Authorization header to the preference API.
2. Authentication middleware validates the token and identifies the authenticated customer.
3. The controller routes the request to the preference service.
4. The service reads the current preference record or validates the new preference payload.
5. On successful update, the service persists the new preferences, publishes the event, and appends audit metadata.
6. The API returns a JSON response for success or an RFC 7807 problem payload for validation or security failures.

## Technology Choices

- Node.js with Express or Python with FastAPI: chosen because both are well-suited to building secure REST APIs quickly while satisfying the requirement to support either option.
- JSON payload contracts: align with the requirement for consistent request/response semantics and easier documentation.
- JWT-based security: satisfies the requirement for standard authentication and authorization through the Authorization header.
- Mock event publisher: supports the requirement for a lightweight event-based integration without requiring external broker dependencies in the development environment.
- Local audit storage: satisfies the requirement for indefinite retention in a development-friendly format without introducing unnecessary operational complexity.

## Risks

- Security risk: customer IDs must never be inferred from token claims without validation; authorization logic must enforce ownership boundaries.
- Data consistency risk: the preference update, event publication, and audit logging must all complete as a coherent transaction or be safely retried.
- Extensibility risk: a fixed schema can become rigid if future channels are added without a clear validation strategy.
- Operational risk: the mock event publisher and local audit storage are development-friendly but not production-grade without later replacement.

## Approval

- Status: Approved
- Reviewer: user
- Notes: Approved to proceed to design review.
