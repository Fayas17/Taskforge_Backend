# TaskForge Backend

A production-grade distributed backend system built to demonstrate expertise in FastAPI,
Celery, Redis, and PostgreSQL. The system is designed to handle large-scale data ingestion
(CSV uploads / high-volume API ingress) asynchronously — decoupling the API layer from
heavy processing work.

---

## Currently Implemented

### Authentication Module
- User registration with bcrypt password hashing
- Local login with JWT access + refresh token pair (cookie-based, HttpOnly)
- Google OAuth2 login via Authlib (OpenID Connect)
- Refresh token rotation — old token revoked on every refresh
- Token revocation using JTI hashing (SHA-256) stored in PostgreSQL
- Device, IP address, and user-agent tracking per refresh token
- Logout with cookie clearing and DB-level token invalidation
- `GET /auth/me/` — fetch authenticated user profile

### Infrastructure
- Async SQLAlchemy 2.0 with asyncpg driver — non-blocking DB operations
- Alembic migrations — versioned schema management (`auth.users`, `auth.refresh_tokens`)
- Redis-backed rate limiting via SlowAPI (per-IP, per-route limits)
- Structured JSON logging via structlog with request_id tracing
- Dedicated security audit log (`logs/security.log`) with 1-year retention
- Request logging middleware — captures method, path, IP, duration (ms)
- Google OAuth integration via Authlib with session middleware
- Multi-stage Docker build (builder → slim runtime image)
- docker-compose with PostgreSQL 15, Redis 7, and a separate test database
- GitHub Actions CI: lint (ruff) → type check (mypy strict) → security audit (pip-audit) → tests → Docker build
- Pre-commit hooks: ruff format, ruff lint, mypy, YAML/TOML validation, private key detection

### Testing
- Unit tests: JWT token creation, password hashing/verification
- Integration tests: register, login, logout, token refresh, `GET /me`, rate limiting, security edge cases
- Savepoint-based transaction rollback — each test is fully isolated, no data pollution
- Separate test PostgreSQL instance (port 5433)
- In-memory Redis for rate limiter tests

---

## Problem Statement

Large CSV uploads or high-volume API ingress cause:
- API timeouts on synchronous processing
- Poor user experience with no progress feedback
- No retry mechanism when processing fails
- No audit trail for failures

**Solution:** Decouple ingestion from processing. The API accepts the upload immediately,
queues it, and returns a job ID. A Celery worker processes the data asynchronously, with
progress tracking, per-row error capture, and automatic retries.

---

## Architecture

```
                          ┌─────────────────────────────────┐
                          │           Client                │
                          └────────────┬────────────────────┘
                                       │ HTTP Request
                          ┌────────────▼────────────────────┐
                          │         FastAPI App              │
                          │  ┌──────────┐  ┌─────────────┐  │
                          │  │   Auth   │  │  Jobs (WIP) │  │
                          │  │  Module  │  │   Module    │  │
                          │  └──────────┘  └──────┬──────┘  │
                          │   Middleware Stack     │         │
                          │  (Rate limit, Logging) │         │
                          └────────┬───────────────┼─────────┘
                                   │               │ Enqueue task
                    ┌──────────────▼──┐    ┌───────▼──────────┐
                    │   PostgreSQL    │    │      Redis        │
                    │  ┌───────────┐  │    │  (Message Broker) │
                    │  │auth schema│  │    │  (Rate Limiter)   │
                    │  │job schema │  │    └───────┬──────────┘
                    │  │(JSONB)    │  │            │ Dequeue task
                    │  └───────────┘  │    ┌───────▼──────────┐
                    └─────────────────┘    │  Celery Worker   │
                             ▲             │  (CSV Processor) │
                             └─────────────┘  (WIP)
```

---

## System Components

| Component | Role |
|-----------|------|
| **FastAPI** | API layer — handles HTTP requests, auth, file ingestion, job dispatch |
| **PostgreSQL** | Primary datastore — user data, tokens, job state, processed rows (JSONB) |
| **Redis** | Dual role: Celery message broker + rate limiter backend |
| **Celery** | Async worker — processes CSV rows in chunks, handles retries, updates job progress |
| **Alembic** | Database migration management — versioned, reproducible schema changes |
| **structlog** | Structured JSON logging with request-scoped context variables |
| **slowapi** | Redis-backed per-IP rate limiting on sensitive endpoints |
| **Authlib** | Google OAuth2 / OpenID Connect integration |

---

## Data Flow

### Auth Flow (Implemented)
```
1. POST /auth/register/     → hash password → INSERT auth.users
2. POST /auth/login/        → verify password → issue JWT pair → SET cookies
3. GET  /auth/me/           → validate access token → SELECT auth.users
4. POST /auth/refresh/      → validate refresh token → rotate → SET new cookies
5. POST /auth/logout/       → revoke refresh token → CLEAR cookies
6. GET  /auth/google/login/ → redirect to Google OAuth consent
7. GET  /auth/google/callback/ → exchange code → upsert user → SET cookies
```

### Ingestion Flow (Planned)
```
1. POST /jobs/upload/       → validate CSV → save file → INSERT job.jobs (status=pending)
2.                          → celery_app.send_task() → push to Redis queue → return job_id
3. Celery worker            → dequeue task → open file → process rows in chunks
4.                          → INSERT job.job_data rows (JSONB per row)
5.                          → UPDATE job.jobs (processed_rows++, status=processing)
6.                          → on completion: UPDATE status=completed, result_data (JSONB)
7.                          → on row failure: append to error_detail (JSONB), failed_rows++
8. GET  /jobs/{id}/         → return job status + progress + result_data
```

---

## Tech Stack Justification

**FastAPI** — async-first, automatic OpenAPI docs, Pydantic v2 validation, native dependency
injection. Handles concurrent connections efficiently with a single worker process using
Python's asyncio event loop.

**PostgreSQL + JSONB** — relational integrity for structured data (users, tokens, job
metadata), JSONB for schema-flexible row storage (each CSV row stored as JSON). JSONB is
indexed and queryable — not just a blob.

**Redis** — low-latency message broker for Celery task queues. Also used as rate limiter
backend. Single service, two responsibilities.

**Celery** — battle-tested distributed task queue. Supports retries with exponential
backoff, task routing to named queues, soft/hard time limits, and result storage.
`task_acks_late=True` ensures tasks are not lost if a worker crashes mid-processing.

**SQLAlchemy 2.0 (async)** — modern async ORM with type-safe mapped columns. Uses asyncpg
driver for FastAPI and psycopg2 for Celery (sync) — strict separation prevents event loop
conflicts.

**Alembic** — version-controlled schema migrations. Supports autogenerate from SQLAlchemy
models. Every schema change is a versioned, reviewable, rollback-capable file.

---

## Security

| Feature | Implementation |
|---------|---------------|
| Password hashing | bcrypt via passlib |
| JWT signing | HS256, configurable expiry (15 min access, 7 day refresh) |
| Token revocation | JTI hashed with SHA-256, stored in `auth.refresh_tokens` |
| Token rotation | Old refresh token revoked on every `/auth/refresh/` call |
| Cookie security | HttpOnly, Secure (configurable), SameSite=lax |
| Rate limiting | Redis-backed SlowAPI — 3/min register, 5/min login, 10/min refresh |
| OAuth2 | Google OpenID Connect — no password stored for OAuth users |
| Audit logging | Dedicated `logs/security.log` — all auth events logged with IP + device |
| Device tracking | IP, user-agent, and device stored per refresh token |
| Dependency scanning | pip-audit in CI pipeline — known CVEs documented and tracked |

---

## Scalability Strategy

**Horizontal worker scaling:** Celery workers are stateless. Add more worker containers
pointing at the same Redis broker to increase processing throughput. Each worker processes
one CSV task at a time (`worker_prefetch_multiplier=1`) to prevent head-of-line blocking.

**Queue isolation:** CSV processing tasks route to a dedicated `csv_processing` queue.
Future task types (email, exports, webhooks) get separate queues — no one workload starves
another.

**Async API layer:** FastAPI with asyncpg handles thousands of concurrent connections on
a single process. DB operations never block the event loop.

**Schema separation:** `auth` and `job` PostgreSQL schemas are logically isolated. Each
module owns its schema — no cross-module table joins in the hot path.

---

## Failure Handling

### Currently in place
- Refresh token revocation on logout prevents reuse after session end
- Database rollback on integrity errors (duplicate email/username)
- JWT validation with type checking (access vs refresh token type enforcement)
- Rate limiting prevents brute-force on login/register

### Planned (Jobs module)
- **Celery retries:** `max_retries=3` with exponential backoff (60s, 120s, 240s)
- **`task_acks_late=True`:** task message only ACKed after completion — worker crash
  returns the task to the queue automatically
- **Per-row error capture:** failed rows stored in `error_detail` JSONB with row index,
  error message, and raw data — user can inspect and retry
- **Idempotent retries:** task checks `job.status == "completed"` before re-processing;
  partial `job_data` rows are cleared before a retry run
- **Soft time limit:** `SoftTimeLimitExceeded` caught gracefully — job marked failed with
  partial progress preserved

---

## Deployment

### Local Development
```bash
docker-compose up --build
# FastAPI:  http://localhost:8000
# Docs:     http://localhost:8000/docs
```

### Database Migrations
```bash
# Create a new migration after model changes
alembic revision --autogenerate -m "description"

# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1
```

### Docker
Multi-stage Dockerfile:
- **Builder stage:** installs build tools, compiles Python wheels from requirements
- **Runtime stage:** `python:3.11-slim`, copies pre-built wheels — minimal final image

### Environment
All secrets and config loaded from `.env` via Pydantic `BaseSettings`. Required vars:
`SECRET_KEY`, `POSTGRES_*`, `REDIS_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`,
`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`.

### Production Checklist
- [ ] Set `COOKIE_SECURE=true` and `DEBUG=false`
- [ ] Set `CORS_ORIGINS` to exact frontend domain (not `*`)
- [ ] Rotate `SECRET_KEY` and store in a secrets manager (not `.env`)
- [ ] Configure `pool_size` and `max_overflow` on the SQLAlchemy engine
- [ ] Enable `celery_worker` service in docker-compose (or deploy as separate container)
- [ ] Set up log aggregation (Datadog, Loki, CloudWatch)

---

## Roadmap

| Feature | Status |
|---------|--------|
| User registration + login (local) | Done |
| Google OAuth2 | Done |
| JWT rotation + revocation | Done |
| Alembic migrations | Done |
| CSV upload endpoint | Planned |
| Celery worker + task definitions | Planned |
| Job progress tracking (JSONB) | Planned |
| Per-row error capture + retry | Planned |
| Prometheus `/metrics` endpoint | Planned |
| OpenTelemetry distributed tracing | Planned |
| Celery Flower monitoring UI | Planned |
| Dead-letter queue for failed tasks | Planned |
| WebSocket / SSE progress streaming | Planned |
