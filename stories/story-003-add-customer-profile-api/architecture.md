# Architecture

## Context

The approved requirements specify a customer profile API endpoint that allows authenticated customers to retrieve their own profile information (Customer ID, First name, Last name, Email). The API must enforce authentication via Bearer tokens (JWT), use RESTful conventions with SQL persistence, auto-generate OpenAPI documentation, and handle error cases gracefully.

## Proposed Components

### 1. Authentication Middleware
- Validates JWT Bearer tokens from request headers
- Extracts customer identity from token claims
- Rejects requests with missing or invalid tokens (401 Unauthorized)

### 2. Profile Controller / Endpoint Handler
- Routes GET requests to `/api/v1/customers/{customerId}/profile`
- Validates that authenticated customer ID matches the requested customer ID (AC4)
- Delegates profile retrieval to the profile service

### 3. Profile Service
- Retrieves customer profile from database
- Returns 404 Not Found if customer does not exist (AC3)
- Encapsulates business logic for profile access rules

### 4. Customer Repository/Data Access Layer
- Queries customer table for profile data
- Returns structured profile objects (customerId, firstName, lastName, email)
- Handles database connection and error handling

### 5. OpenAPI/Swagger Documentation Generator
- Auto-generates API documentation from endpoint definitions
- Remains synchronized with code through build-time generation
- Provides interactive endpoint testing interface

### 6. Error Handling / Response Formatter
- Formats API responses consistently in JSON
- Maps exceptions to appropriate HTTP status codes
- Ensures no sensitive data (passwords, tokens) leaks to logs or responses

## Data Flow

1. **Client Request:** Client sends GET request with JWT Bearer token
   - `GET /api/v1/customers/{customerId}/profile`
   - Header: `Authorization: Bearer <JWT_TOKEN>`

2. **Authentication:** Middleware validates token
   - Extracts customer ID from token claims
   - Returns 401 if token invalid or missing

3. **Authorization Check:** Controller verifies customer is accessing own profile
   - Compares `{customerId}` in URL with token's customer ID claim
   - Returns 403 if mismatch (security boundary)

4. **Profile Retrieval:** Service queries database
   - Repository executes SELECT on customers table
   - Returns profile data or null

5. **Response Formation:**
   - If found: HTTP 200 with profile JSON object
   - If not found: HTTP 404 with error response
   - All errors: JSON error object with code and message

6. **Documentation:** OpenAPI spec reflects this flow automatically

## Technology Choices

### Language & Framework
- **Selection:** Python with Flask/FastAPI (or Node.js/Express)
- **Rationale:** Lightweight, rapid API development, good JWT library support, integrates with existing application

### Authentication
- **Selection:** JWT (JSON Web Tokens) with Bearer scheme
- **Rationale:** Stateless, scalable, industry standard, no session storage needed

### Database
- **Selection:** SQL relational database (PostgreSQL or MySQL)
- **Rationale:** ACID compliance for customer data integrity, structured schema, supports transactions

### API Documentation
- **Selection:** OpenAPI 3.0 / Swagger
- **Rationale:** Auto-generated from annotations/decorators, stays in sync, provides interactive testing

### HTTP Status Codes
- **200 OK:** Successful profile retrieval
- **400 Bad Request:** Malformed request
- **401 Unauthorized:** Missing or invalid authentication
- **403 Forbidden:** Customer accessing another customer's profile
- **404 Not Found:** Customer does not exist
- **500 Internal Server Error:** Unexpected server error

## Risks

### Risk 1: Authentication Bypass
- **Description:** Weak JWT validation or token leakage could bypass security
- **Mitigation:** Use well-tested JWT library, enforce token expiration, HTTPS only, secrets in environment variables

### Risk 2: Authorization Bypass (AC4 Violation)
- **Description:** Middleware failure could allow customer to access others' profiles
- **Mitigation:** Unit tests for authorization logic, explicit customer ID comparison, separation of concerns

### Risk 3: Sensitive Data Leakage
- **Description:** Customer data or tokens appearing in logs
- **Mitigation:** Log only non-sensitive fields, sanitize request/response logging, security code review

### Risk 4: Database Performance
- **Description:** High profile request volume could strain database
- **Mitigation:** Index customer ID, consider caching for read-heavy workload, monitor query performance

### Risk 5: API Documentation Drift
- **Description:** Manual documentation updates could fall out of sync
- **Mitigation:** Auto-generation from code, CI validation that docs build successfully

## Approval

- Status: Approved
- Reviewer: User
- Notes: Architecture approved. Ready for design review.
