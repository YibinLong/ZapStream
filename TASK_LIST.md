## Zapier Triggers API — Task List

**Status Legend:** ⬜ Not Started | 🟦 In Progress | ✅ Done | ❌ Blocked

---

## PHASE 1: Backend Project Setup ✅

### Epic 1.1: Initialize FastAPI app and local environment ✅

**Story:** Bootstrap Python project, config loading, and CORS

- ✅ Task 1.1.1: Create backend structure `backend/` (`main.py`, `models.py`, `auth.py`, `rate_limit.py`, `logging.py`, `storage/{base.py,sqlite.py,dynamodb.py}`)
- ✅ Task 1.1.2: Add `requirements.txt` (FastAPI, Uvicorn, SQLModel, pydantic, httpx, pytest, boto3, structlog or python-json-logger)
- ✅ Task 1.1.3: Add `.gitignore` entries for Python, env, and `data/` as per PRD
- ✅ Task 1.1.4: Add `.env.example` with all variables from PRD and load config in code
- ✅ Task 1.1.5: Implement `backend/main.py` with FastAPI instance, CORS from `CORS_ALLOWED_ORIGINS`, and health route
- ✅ Task 1.1.6: Add dev command (Makefile `dev` or shell script) to run `uvicorn backend.main:app --reload --port ${BACKEND_PORT:-8000}`

**Acceptance:** Local server starts on port 8000 with CORS enabled and a health endpoint returning 200. ✅

---

## PHASE 2: Storage Abstraction ✅

### Epic 2.1: Define models and storage interface ✅

**Story:** Represent events and abstract storage for SQLite (local) and DynamoDB (prod)

- ✅ Task 2.1.1: Define Pydantic/SQLModel models (Event schema with fields per PRD)
- ✅ Task 2.1.2: Create `storage/base.py` interface (create_event, get_pending, ack_event, delete_event, get_event_by_id, get_by_idempotency)
- ✅ Task 2.1.3: Implement `storage/sqlite.py` with SQLModel + SQLite at `./data/events.db`
- ✅ Task 2.1.4: Implement optional `storage/dynamodb.py` skeleton (behind env flag; not required for local dev)

**Acceptance:** SQLite works locally: can insert, list pending, ack, and delete events; idempotency lookup returns existing event when applicable. ✅

---

## PHASE 3: Auth & Multi‑Tenancy ✅

### Epic 3.1: API key parsing and tenant scoping ✅

**Story:** Extract API key from headers and map to tenant

- ✅ Task 3.1.1: Parse `Authorization: Bearer` or `X-API-Key` header
- ✅ Task 3.1.2: Map API key → `tenantId` from `API_KEYS` env (comma-separated `key=tenant` pairs)
- ✅ Task 3.1.3: Attach `tenantId` to request context (dependency/middleware)
- ✅ Task 3.1.4: Return 401 for missing/invalid key

**Acceptance:** Requests without a valid API key receive 401; downstream handlers can read `tenantId` from context. ✅

---

## PHASE 4: Event Ingestion API (POST /events) ✅

### Epic 4.1: Accept, validate, and persist events ✅

**Story:** Validate payload, enforce size, idempotency, and write to storage

- ✅ Task 4.1.1: Define request/response models; validate payload is JSON object and ≤ `MAX_PAYLOAD_BYTES`
- ✅ Task 4.1.2: Implement `POST /events` creating pending event with `delivered=false` and `status=pending`
- ✅ Task 4.1.3: Support `X-Idempotency-Key`; return existing event ID for duplicates (409 semantics per PRD)
- ✅ Task 4.1.4: Implement in-memory rate limit per API key (`RATE_LIMIT_PER_MINUTE`), return 429 with `Retry-After`

**Acceptance:** Returns 200 with `{ id, receivedAt, status: "accepted" }`; duplicate idempotency returns existing event; 400/401/409/429 handled as specified. ✅

---

## PHASE 5: Inbox API (GET /inbox, ACK, DELETE) ✅

### Epic 5.1: List undelivered events with filters and pagination ✅

**Story:** Pull-based inbox for pending events

- ✅ Task 5.1.1: Implement `GET /inbox` with query params: `limit` (default 50, max 500), `since` (ISO), `topic`, `type`
- ✅ Task 5.1.2: Order by `createdAt` ASC and return `nextCursor` (encode `createdAt|id`)
- ✅ Task 5.1.3: Validate query params and return 400 for invalid values

### Epic 5.2: Acknowledge and delete events ✅

**Story:** Mark events delivered or delete to prevent duplicates

- ✅ Task 5.2.1: Implement `POST /inbox/{id}/ack` (idempotent) setting `delivered=true`, `status=acknowledged`
- ✅ Task 5.2.2: Implement `DELETE /inbox/{id}` (hard delete in SQLite; soft-delete optional)
- ✅ Task 5.2.3: Enforce tenant ownership; return 404 if not found; 409 for invalid state transitions

**Acceptance:** Clients can list pending events, page via cursor, ack or delete by id with correct tenancy and state checks. ✅

---

## PHASE 6: Observability & Error Handling ✅

### Epic 6.1: Structured logging and request tracing ✅

**Story:** JSON logs with correlation and tenant context

- ✅ Task 6.1.1: Configure structured JSON logging with `LOG_LEVEL`/`DEBUG`
- ✅ Task 6.1.2: Add requestId middleware; include `X-Request-ID` in responses
- ✅ Task 6.1.3: Include `tenantId` when available in logs; avoid logging secrets

### Epic 6.2: Consistent error responses ✅

**Story:** Standard error envelope per PRD appendix

- ✅ Task 6.2.1: Implement error handlers returning
  `{ "error": { "code": ..., "message": ..., "requestId": ... } }`

**Acceptance:** Logs are structured and include requestId/tenantId; errors follow the documented schema. ✅

---

## PHASE 7: Testing & Quality ✅

### Epic 7.1: Unit and API tests ✅

**Story:** Validate endpoints, auth, idempotency, and limits

- ✅ Task 7.1.1: Set up pytest/httpx test harness
- ✅ Task 7.1.2: Unit tests: schema validation, auth middleware, idempotency logic
- ✅ Task 7.1.3: API tests: `POST /events` (happy path, invalid JSON, 401, 409), `GET /inbox`, ack/delete
- ✅ Task 7.1.4: Concurrency tests for idempotent POST with same key
- ✅ Task 7.1.5: Rate limit tests expecting 429 with `Retry-After`
- ✅ Task 7.1.6: Add basic coverage threshold (80%)

**Acceptance:** All tests pass locally; coverage threshold met. ✅

---

## PHASE 8: Frontend-Backend Integration ⬜

### Epic 8.1: Connect Frontend to Real Backend Data ⬜

**Story:** Replace mock data in frontend dashboard with real API data

- ⬜ Task 8.1.1: Update Event Stream component to fetch real events from `/inbox` API endpoint
- ⬜ Task 8.1.2: Replace mock statistics cards with real data calculations (event count, success rate, response time)
- ⬜ Task 8.1.3: Implement real-time polling or WebSocket for live event updates
- ⬜ Task 8.1.4: Add API Playground functionality to actually test backend endpoints from UI
- ⬜ Task 8.1.5: Implement proper error handling for API calls (loading states, error messages, retry logic)
- ⬜ Task 8.1.6: Update System Status panel to show real backend connectivity status

**Acceptance:** Dashboard displays live data from backend API; new events appear automatically; API Playground successfully calls backend.

### Epic 8.2: Real-time Features ⬜

**Story:** Add live event streaming and notifications

- ⬜ Task 8.2.1: Implement WebSocket or Server-Sent Events for real-time event updates
- ⬜ Task 8.2.2: Add event creation form in frontend Playground tab
- ⬜ Task 8.2.3: Add event acknowledgment and deletion UI in dashboard
- ⬜ Task 8.2.4: Implement real-time statistics updates when events are created/updated
- ⬜ Task 8.2.5: Add notification system for new events and system alerts

**Acceptance:** Users can create, acknowledge, and delete events from frontend; all updates appear in real-time without page refresh.

---

## PHASE 9: Developer Experience ⬜

### Epic 9.1: Scripts and docs for local dev ⬜

**Story:** Make local iteration fast and predictable

- ⬜ Task 9.1.1: Provide Makefile targets (`dev`, `test`, optionally `lint`)
- ⬜ Task 9.1.2: Ensure `.env.example` + quickstart steps are discoverable alongside the backend

**Acceptance:** One command to run server with reload; one command to run tests; env config is clear.

---

Notes:
- Frontend UI and AWS deployment are considered done; this list focuses on remaining backend/API work per PRD.
- Production DynamoDB module can remain a stub initially; local dev must run entirely on SQLite.


