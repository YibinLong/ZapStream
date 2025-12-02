# ZapStream

A real-time event ingestion and delivery API with a live dashboard. Think of it as infrastructure for Zapier-like workflows—you POST events, and your automations pull them from an inbox.

![Next.js](https://img.shields.io/badge/Next.js-16-black)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![Python](https://img.shields.io/badge/Python-3.9+-3776AB)
![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6)

## What It Does

- **Event Ingestion** → POST JSON events to `/events`, get back an event ID
- **Event Inbox** → GET `/inbox` to pull undelivered events with filtering/pagination
- **Event Management** → Acknowledge or delete events to prevent duplicates
- **Real-time Streaming** → SSE endpoint for live event updates
- **Multi-tenant** → API key-based isolation per tenant

## Quick Start

```bash
# Clone and enter the project
git clone <repository-url>
cd ZapStream

# One-command setup (creates venv, installs deps, inits DB, runs tests)
make quickstart

# Start both servers (frontend: 3000, backend: 8000)
make dev
```

**That's it.** Open http://localhost:3000 for the dashboard, http://localhost:8000/docs for API docs.

### Manual Setup (if needed)

```bash
# 1. Environment
make env-setup                    # Creates .env from template

# 2. Backend
make setup-backend                # Python venv + dependencies
make db-init                      # Initialize SQLite database

# 3. Frontend
npm install                       # Node.js dependencies

# 4. Run
make dev                          # Start both servers
```

## Project Structure

```
ZapStream/
├── app/                    # Next.js frontend (App Router)
│   ├── page.tsx           # Dashboard page
│   └── globals.css        # Styles + theme
├── components/            # React components
│   ├── event-log.tsx      # Live event stream viewer
│   ├── api-playground.tsx # Interactive API tester
│   └── connection-status.tsx
├── backend/               # FastAPI backend
│   ├── main.py           # App entry, routes, middleware
│   ├── models.py         # Pydantic schemas
│   ├── auth.py           # API key authentication
│   └── storage/          # SQLite (dev) / DynamoDB (prod)
└── tests/                 # pytest test suite
```

## API Reference

All endpoints require authentication via one of:
- `Authorization: Bearer <API_KEY>`
- `X-API-Key: <API_KEY>`
- `?api_key=<API_KEY>` (for SSE streams)

Default dev key: `dev_key_123`

### POST /events
Send a new event:
```bash
curl -X POST http://localhost:8000/events \
  -H "Authorization: Bearer dev_key_123" \
  -H "Content-Type: application/json" \
  -d '{"source": "billing", "type": "invoice.paid", "payload": {"amount": 4200}}'
```

### GET /inbox
List undelivered events:
```bash
curl "http://localhost:8000/inbox?limit=50&topic=finance" \
  -H "Authorization: Bearer dev_key_123"
```

### POST /inbox/{id}/ack
Mark event as acknowledged:
```bash
curl -X POST http://localhost:8000/inbox/evt_123/ack \
  -H "Authorization: Bearer dev_key_123"
```

### DELETE /inbox/{id}
Delete an event:
```bash
curl -X DELETE http://localhost:8000/inbox/evt_123 \
  -H "Authorization: Bearer dev_key_123"
```

### GET /inbox/stream
Real-time event stream (SSE):
```bash
curl "http://localhost:8000/inbox/stream?api_key=dev_key_123"
```

### GET /health
Health check (no auth required):
```bash
curl http://localhost:8000/health
```

## Development Commands

```bash
# Servers
make dev              # Both frontend + backend
make dev-frontend     # Frontend only (port 3000)
make dev-backend      # Backend only (port 8000)

# Testing
make test             # Run all tests
make test-backend-cov # Tests with coverage report

# Code Quality
make lint             # Lint everything
make lint-backend-fix # Auto-fix backend issues

# Database
make db-init          # Initialize SQLite
make db-reset         # Wipe and recreate

# Utilities
make status           # Show environment status
make health-check     # Verify setup
make clean            # Remove caches/temp files
```

## Configuration

Create `.env` from `.env.example` (or run `make env-setup`):

```env
# Frontend
NEXT_PUBLIC_ZAPSTREAM_API_URL=http://localhost:8000
NEXT_PUBLIC_ZAPSTREAM_API_KEY=dev_key_123

# Backend
APP_ENV=development
BACKEND_PORT=8000
API_KEYS=dev_key_123=tenant_dev
STORAGE_BACKEND=sqlite
DATABASE_URL=sqlite:///./data/events.db
RATE_LIMIT_PER_MINUTE=60
MAX_PAYLOAD_BYTES=524288
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, Python 3.9+, Pydantic |
| Database | SQLite (dev), DynamoDB (prod) |
| Real-time | Server-Sent Events (SSE) |
| Testing | pytest, httpx |

## Production Deployment

For production, switch to DynamoDB:

1. Set `STORAGE_BACKEND=dynamodb` in environment
2. Create DynamoDB table with:
   - Partition key: `tenantId` (String)
   - Sort key: `eventId` (String)
3. Configure AWS credentials via IAM role or env vars

See `DEPLOYMENT_GUIDE.md` for full AWS setup instructions.

## License

MIT
