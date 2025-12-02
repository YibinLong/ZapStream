++ Product Requirements Document (PRD) — Zapier Triggers API (Backend)

This PRD is written for a solo developer working with an AI coding assistant. It is explicit enough for the AI to build, test, and run the backend locally. The existing frontend and AWS deployment are already correct and MUST remain unchanged; the backend API described here will integrate with them as-is.


Input Placeholders (fill or keep defaults)
- PROJECT_NAME: Zapier Triggers API
- APP_TO_CLONE or SHORT_DESCRIPTION: Unified, real-time event ingestion and delivery API
- Platform: WEB
- Constraints: Python + FastAPI backend; AWS in production; local dev must run without AWS
- Special Notes: Frontend and deployment are already done and correct; do not change their behavior or contracts. Add CORS to allow existing frontend origin(s).


### 1. Project Summary
Build a unified, real-time event ingestion API to achieve standardized, reliable triggers delivery for Zapier-like workflows. MVP scope: ingest events via POST /events; list undelivered events via GET /inbox; acknowledge/delete events when consumed.

Assumptions
- The existing frontend and AWS deployment are correct and will not be modified.
- Local development must run entirely without AWS. Production will use AWS services.
- Multi-tenant support via API keys; each API key represents a tenant (e.g., an integration/app).
- A simple “inbox” pull model is sufficient for MVP (no webhooks push from this service in MVP).


### 2. Core Goals
- Users can send JSON events to POST /events and receive an acknowledgment with an event ID.
- Users can list undelivered events via GET /inbox (optionally filtered) to power real-time workflows.
- Users can acknowledge/delete individual events so they are not delivered twice.
- Users can authenticate using API keys; unauthorized requests are rejected with clear errors.


### 3. Non-Goals
- Advanced event filtering, transformation, or routing logic.
- Long-term data retention or archival beyond MVP needs.
- Analytics dashboards, complex monitoring UIs, or BI exports.
- External push delivery (webhooks) from this service (pull-based inbox only for MVP).


### 4. Tech Stack (Solo-AI Friendly)
- FastAPI (Python) — modern, async-friendly, excellent docs and ecosystem; easy for LLMs.
- Uvicorn — fast ASGI server; standard for FastAPI local dev and containers.
- SQLModel + SQLite (local dev) — typed models on SQLAlchemy; zero external setup.
- DynamoDB (prod) — serverless durability and scale on AWS; simple schema for events.
- boto3 (prod) — AWS SDK for Python; standard, well-documented.
- httpx + pytest — straightforward API testing; good examples and LLM familiarity.
- pydantic — schema validation and helpful error messages.
- python-json-logger / structlog — structured logs for observability, toggle-able via env.

Rationale: This stack uses highly documented, familiar tools that are simple to run locally and scale in AWS, with clear patterns an AI can follow.


### 5. Feature Breakdown — Vertical Slices

Feature: Event Ingestion (POST /events)
- User Story: As a developer, I want to POST JSON events so I can trigger workflows in real time.
- Acceptance Criteria:
  - Accepts Content-Type: application/json with a payload up to 512KB.
  - Requires Authorization: Bearer <API_KEY> or X-API-Key header.
  - Returns 200 with { id, receivedAt, status: "accepted" }.
  - Supports X-Idempotency-Key to safely retry without duplicating events.
  - Validates schema: payload must be a JSON object; optional fields source, type, topic.
  - Persists event durably with status=pending (undelivered) and delivered=false.
- Data Model Notes:
  - Event: id (UUIDv7 or ULID), tenantId, source, type, topic, payload (JSON), createdAt,
    delivered (bool), status (pending|acknowledged|deleted), idempotencyKey (optional).
  - Local dev: SQLite file database stored at ./data/events.db.
  - Prod: DynamoDB table with PK (tenantId) and SK (eventId), GSI on status (optional).
- Edge Cases & Errors:
  - 400 if payload is not JSON object or exceeds size limit.
  - 401 if missing/invalid API key.
  - 409 if idempotency key already exists for same tenant; return existing event ID.
  - 429 if rate limit exceeded (simple token bucket in-memory for dev; WAF/API Gateway in prod).

Feature: Inbox Listing (GET /inbox)
- User Story: As an automation system, I want to fetch undelivered events so I can process them.
- Acceptance Criteria:
  - Requires auth (per-tenant view).
  - Supports query params: limit (default 50, max 500), since (ISO timestamp), topic, type.
  - Returns list of undelivered events ordered by createdAt ASC, and a nextCursor for pagination.
  - Includes stable IDs and payloads for consumption by existing frontend/agents.
- Data Model Notes:
  - Query pending events where delivered=false and status=pending for the tenant.
  - Implement simple cursor based on createdAt and id.
- Edge Cases & Errors:
  - 400 for invalid limit or malformed since.
  - 401 if auth fails.
  - Empty list is valid when no pending events.

Feature: Acknowledge/Delete (POST /inbox/{id}/ack and DELETE /inbox/{id})
- User Story: As an automation system, I want to mark events completed to avoid duplicates.
- Acceptance Criteria:
  - POST /inbox/{id}/ack marks delivered=true and status=acknowledged; idempotent (200 OK even if already acked).
  - DELETE /inbox/{id} hard-deletes the event (or marks status=deleted if soft-delete).
  - Requires auth (event must belong to tenant).
- Data Model Notes:
  - Updates are conditional on tenant ownership and current state.
  - Option to soft-delete (status=deleted) to keep audit trail; SQLite can hard-delete for simplicity.
- Edge Cases & Errors:
  - 404 if event not found for tenant.
  - 409 on conflicting state transitions (deleted → ack not allowed); return clear message.

Feature: Authentication & Multi-Tenancy
- User Story: As a platform, I need to secure endpoints per tenant.
- Acceptance Criteria:
  - Support two header formats: Authorization: Bearer <API_KEY> or X-API-Key: <API_KEY>.
  - API keys are configured via env (MVP) and map to tenant IDs.
  - All reads/writes scoped by tenantId resolved from API key.
- Data Model Notes:
  - In MVP, API key → tenantId map loaded from env on startup.
  - Future: move to DB-backed or AWS Secrets Manager.
- Edge Cases & Errors:
  - 401 for missing/invalid key.
  - 403 if key valid but tenant disabled (future flag).

Feature: Observability & Rate Limiting
- User Story: As an operator, I want structured logs and basic protections.
- Acceptance Criteria:
  - Structured JSON logs with requestId and tenantId when available.
  - DEBUG toggle via env enables verbose logs.
  - Basic rate limit per API key in local dev (in-memory); recommend WAF/API Gateway for prod.


### 8. .env Setup
Why: Enables local dev without AWS, and production configuration with AWS.

Example .env (local dev)
```env
APP_ENV=development
PORT=8000
LOG_LEVEL=INFO
DEBUG=true

# CORS (set to your existing frontend origin; keep deployment unchanged)
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://your-existing-frontend.example.com

# Authentication (MVP: comma-separated key=tenant pairs)
# Example: "key1=tenant_a,key2=tenant_b"
API_KEYS=dev_key_123=tenant_dev

# Storage selection
STORAGE_BACKEND=sqlite             # sqlite | dynamodb
DATABASE_URL=sqlite:///./data/events.db

# Optional AWS config (only used when STORAGE_BACKEND=dynamodb)
AWS_REGION=us-east-1
AWS_DYNAMODB_TABLE=triggers_events
# For local dev we do not require AWS credentials.
# In production use IAM role or environment variables:
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=

# Request limits
MAX_PAYLOAD_BYTES=524288           # 512KB
RATE_LIMIT_PER_MINUTE=60

# Idempotency window in minutes (clean-up policy)
IDEMPOTENCY_TTL_MIN=60
```

Manual steps required when adding/changing .env
1) What: Set CORS_ALLOWED_ORIGINS to your existing frontend origin(s).
   Where: .env file in the backend project root.
   Why: Allows the unchanged frontend to call this API in browsers.
2) What: Define API_KEYS mapping (key=tenant).
   Where: .env.
   Why: Secures multi-tenant access for MVP without DB.
3) What: Choose STORAGE_BACKEND=sqlite for local dev.
   Where: .env.
   Why: Avoids AWS setup locally; fastest DX.


### 9. .gitignore
Why: Prevent committing build artifacts, local env, and data. This includes Node/Electron (frontend already exists) and Python backend ignores.

Example .gitignore
```gitignore
# Node / Frontend / Electron
node_modules/
dist/
out/
.next/
.parcel-cache/
*.log
*.map
*.asar
release/

# Env and secrets
.env
.env.*

# Python
__pycache__/
*.py[cod]
*.sqlite
.venv/
venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
coverage.xml

# Local data
data/
```


### 10. Debugging & Logging
Why: Make issues easy to diagnose locally and in prod.

- Backend (FastAPI/Uvicorn):
  - Structured logs (JSON) with fields: timestamp, level, requestId, tenantId, path, method, status.
  - Toggle verbose logging with DEBUG=true and LOG_LEVEL=DEBUG.
  - Attach a requestId (UUID) per request; include in responses as X-Request-ID.
  - Include validation errors with clear messages; never log full secrets.

- If an Electron renderer/main process exists (unchanged frontend):
  - Main process logs to file with rotation (info and error channels).
  - Renderer logs to console in dev; ship minimal logs in prod.
  - Use an IPC-safe logger; do not send sensitive payloads over IPC.
  - If not using Electron, ignore this sub-bullet.


### 11. External Setup Instructions (Manual)
Only needed for production AWS usage. Local dev uses SQLite and requires no AWS resources.

1) DynamoDB Table
   - What: Create table for events storage.
   - Where: AWS Console → DynamoDB → Create Table.
   - Why: Durable, scalable event persistence in production.
   - Settings (MVP):
     - Table name: AWS_DYNAMODB_TABLE (e.g., triggers_events)
     - Partition key (PK): tenantId (String)
     - Sort key (SK): eventId (String)
     - Optional GSI: status-index (PK: tenantId, SK: status_createdAt) to list pending quickly.

2) IAM & Credentials
   - What: Allow the app to read/write the DynamoDB table.
   - Where: AWS Console → IAM.
   - Why: Secure production access.
   - Steps:
     - Create IAM role for the compute environment that runs your backend (reuse your correct deployment).
     - Attach policy with dynamodb:PutItem, GetItem, Query, UpdateItem, DeleteItem for the table.

3) Environment Variables in Deployment
   - What: Set STORAGE_BACKEND=dynamodb, AWS_REGION, AWS_DYNAMODB_TABLE and remove local DATABASE_URL.
   - Where: Your existing deployment environment configuration (keep its mechanism unchanged).
   - Why: Switches storage from SQLite (local) to DynamoDB (prod) transparently.


### 12. Deployment Plan
Local development
- Create and activate a virtual environment.
- Install dependencies.
- Start server with reload.
- Run tests.

Example commands
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
uvicorn app.main:app --reload --port ${PORT:-8000}

# in another terminal
pytest -q
```

Optional Makefile targets (recommended)
```makefile
dev:            # run app with reload
	uvicorn app.main:app --reload --port ${PORT}

test:           # run unit + API tests
	pytest -q

lint:           # run format + lint
	ruff check . && ruff format --check .
```

No changes to your existing deployment
- Keep the current CI/CD and infrastructure unchanged.
- Only ensure the new environment variables in Section 8/11 are set in the deployed environment.


API Surface (for the frontend to consume without changes)

Request Authentication
- Preferred: Authorization: Bearer <API_KEY>
- Alternative: X-API-Key: <API_KEY>

POST /events
```http
POST /events HTTP/1.1
Content-Type: application/json
Authorization: Bearer dev_key_123
X-Idempotency-Key: 1c0f1d10-...

{
  "source": "billing",
  "type": "invoice.paid",
  "topic": "finance",
  "payload": { "invoiceId": "inv_123", "amount": 4200, "currency": "USD" }
}
```
Response
```json
{ "id": "evt_01HH...", "receivedAt": "2025-11-11T10:00:00Z", "status": "accepted" }
```

GET /inbox?limit=50&since=2025-11-11T00:00:00Z&topic=finance&type=invoice.paid
```http
GET /inbox?limit=50&topic=finance HTTP/1.1
Authorization: Bearer dev_key_123
```
Response (200)
```json
{
  "events": [
    {
      "id": "evt_01HH...",
      "createdAt": "2025-11-11T10:00:00Z",
      "source": "billing",
      "type": "invoice.paid",
      "topic": "finance",
      "payload": { "invoiceId": "inv_123", "amount": 4200, "currency": "USD" }
    }
  ],
  "nextCursor": "2025-11-11T10:00:00Z|evt_01HH..."
}
```

POST /inbox/{id}/ack
```http
POST /inbox/evt_01HH.../ack HTTP/1.1
Authorization: Bearer dev_key_123
```
Response (200)
```json
{ "id": "evt_01HH...", "status": "acknowledged" }
```

DELETE /inbox/{id}
```http
DELETE /inbox/evt_01HH... HTTP/1.1
Authorization: Bearer dev_key_123
```
Response (200)
```json
{ "id": "evt_01HH...", "status": "deleted" }
```


Testing Plan (AI-executable)
- Unit tests: schema validation, auth middleware, idempotency.
- API tests: POST /events happy path, invalid JSON, 401 auth, 409 idempotency; GET /inbox; ack/delete flows.
- Concurrency tests: simulate parallel POSTs with same X-Idempotency-Key.
- Rate limit tests: exceed RATE_LIMIT_PER_MINUTE and expect 429.


Directory Structure (suggested)
```text
app/
  main.py            # FastAPI app, routes, middleware, CORS
  models.py          # pydantic & SQLModel definitions
  storage/
    base.py          # interface/abstraction
    sqlite.py        # local impl
    dynamodb.py      # prod impl
  auth.py            # API key parsing and tenant resolution
  rate_limit.py      # in-memory token bucket (dev)
  logging.py         # structured logging setup
tests/
  test_events.py
  test_inbox.py
  test_auth.py
requirements.txt
.env (local only)
```


### 🧱 TASK_LIST.md STRUCTURE
Use Epics → Stories → Tasks.

Epic: Event Ingestion
- Story: POST /events accepts and validates JSON.
  - Task: Define pydantic request/response models.
  - Task: Implement idempotency using header + storage lookup.
  - Task: Persist event (SQLite/DynamoDB via storage abstraction).
  - Task: Return acknowledgment with event ID.
- Story: Rate limiting (dev).
  - Task: Implement in-memory token bucket by API key.
  - Task: Return 429 with Retry-After on exceed.

Epic: Inbox
- Story: List undelivered events.
  - Task: Implement GET /inbox with filters, pagination.
  - Task: Add createdAt|id cursor encoding/decoding.
- Story: Acknowledge/Delete.
  - Task: POST /inbox/{id}/ack sets delivered=true, status=acknowledged.
  - Task: DELETE /inbox/{id} removes or soft-deletes.

Epic: Auth & Multi-Tenancy
- Story: API key middleware.
  - Task: Parse Authorization/X-API-Key.
  - Task: Map to tenantId from env.
  - Task: Attach tenant to request context.

Epic: Observability
- Story: Structured logging.
  - Task: RequestId middleware, JSON logs, X-Request-ID response header.
- Story: Error handling.
  - Task: Consistent error envelope with codes and messages.

Epic: CI/Test
- Story: API tests.
  - Task: Write httpx/pytest tests for all routes and edge cases.
  - Task: Add coverage thresholds.


### 🧩 SOLO-DEV GUARDRAILS
- Minimize ops: SQLite locally; DynamoDB in prod via IAM role; no extra infra.
- Single repo; secrets only in .env (local) or deployment env vars (prod).
- Enforce strict typing where practical (pydantic models, SQLModel types).
- Ship vertical slices; keep routes small and well-tested.
- Avoid overengineering: simple storage abstraction with two implementations.


Appendix: Error Response Format (consistent)
```json
{
  "error": {
    "code": "INVALID_PAYLOAD",
    "message": "Payload must be a JSON object and <= 512KB",
    "requestId": "req_01HH..."
  }
}
```

This completes the backend PRD. The existing frontend and deployment remain unchanged; only configure env vars and AWS table/role (prod) as specified above.*** End Patch``` -->

