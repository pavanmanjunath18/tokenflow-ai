# TokenFlow AI

**Enterprise AI Cost, Usage & Governance Intelligence Platform**

A portfolio-grade full-stack SaaS project that helps companies understand, monitor, and optimise their enterprise AI spend — built with Next.js, FastAPI, PostgreSQL, and a connector-based ingestion architecture.

---

## Problem Statement

Enterprise AI usage is fragmented across browser tools, IDE assistants, internal APIs, Slack bots, and model gateways. Finance teams can't see where AI budget is going. Engineering leads don't know which models are being overused. IT can't identify shadow AI risks. HR and Legal have no visibility into PII exposure.

TokenFlow AI brings all of that into a single governance dashboard.

---

## What it answers

| Question | Feature |
|---|---|
| Where is our AI spend going? | Dashboard overview + date/department/provider filters |
| Which models are being overused? | Model optimisation page |
| Are employees using expensive models for simple tasks? | Expensive-model misuse flags + recommendations |
| Are paid licenses being underused? | License waste detection |
| Are there shadow AI risks? | Governance alerts |
| Are there abnormal cost spikes? | Cost anomaly recommendations |
| What can we do to reduce waste? | Recommendation center with RBAC-gated human review |
| Are connectors healthy? | Integration observability (health, warnings, watermark, duration) |

---

## Privacy & Ethics

This platform is **not employee surveillance software**.

- **Team-first analytics** — individual-level data is admin-restricted
- **No raw prompts stored** — metadata only, PII-redacted by default
- **No automated disciplinary decisions** — all recommendations require human review
- **Audit logging** — every action is logged
- **No employee ranking** — no performance scoring

---

## Architecture

```
Data Sources (CSV/JSONL)
    ↓
Connector Layer (9 connectors — each has a documented production replacement)
    ↓ sync(since=watermark)  ← incremental delta filtering
Ingestion Service (UPSERT + validation log + audit trail)
    ↓
PostgreSQL (11 tables)
    ↓
FastAPI Services (analytics, licenses, recommendations, ingestion)
    ↑↓ enqueue / poll
Arq Worker (background sync tasks, heartbeat cron every 15 min)
    ↑↓ broker + cache
Redis (task queue + integration status cache + heartbeat snapshots)
    ↓
Next.js 16 (App Router, JWT auth, RBAC-gated UI + live polling)
```

---

## Incremental Sync (Watermark)

Every connector sync is incremental by default:

1. Before syncing, the ingestion service queries the `finished_at` of the **most recent successful run** for that source.
2. This timestamp is passed to `connector.sync(since=<datetime>)`.
3. **Time-series connectors** (api_gateway, browser, kafka, clickhouse, kubernetes) filter out rows whose `timestamp < since`, counting them as `rows_skipped`.
4. **Reference-data connectors** (identity, model_pricing, licenses, productivity) always do a full refresh — they're small and have no event timestamp.
5. The `watermark_since` used is recorded on the `IntegrationSyncRun` row for observability.

This simulates real production delta-sync behaviour without changing the CSV architecture. In production, the same `since` timestamp would become the `WHERE timestamp > ?` clause in a ClickHouse query or the Kafka consumer's offset.

---

## Schema-Drift Validation

Every sync run produces row-level validation logs:

- **Schema-level errors** — missing columns detected by `BaseConnector._validate_schema()` before normalization.
- **Row-level warnings** — empty/null required fields detected by `BaseConnector._validate_rows()` after normalization, capped at 100 per run.
- All warnings are written to `ingestion_validation_logs` with `run_id`, `connector_name`, `row_number`, `field_name`, `error_type`, and `raw_value`.
- A connector with any warnings from its last run shows as **Degraded** in the integrations UI.

```
GET /api/integrations/validation-logs?connector=api_gateway   # recent warnings
GET /api/integrations/history                                  # full sync run history
```

---

## Integration Observability

The integrations page shows per-connector health at a glance:

| Field | Source |
|---|---|
| **Health** | healthy / degraded / failed / not_synced / syncing |
| **Rows upserted** | `rows_ingested` on last run |
| **Rows skipped** | `rows_skipped` (watermark-filtered) on last run |
| **Last duration** | `duration_ms` on last run |
| **Warnings** | count of `ingestion_validation_logs` for last run |
| **Last success** | `finished_at` of most recent successful run |
| **Last failure** | `finished_at` of most recent failed run |
| **Watermark** | `watermark_since` used in last run |

Health rules:
- `not_synced` — no run exists
- `syncing` — run has status `running`
- `failed` — last run failed
- `degraded` — last run succeeded but had validation warnings
- `healthy` — last run succeeded with zero warnings

---

## Dashboard Filters

All dashboard endpoints accept optional query parameters:

```
GET /api/dashboard/overview?start_date=2025-01-01&end_date=2025-03-31&department=Engineering
GET /api/dashboard/departments?provider=anthropic
GET /api/dashboard/models?model=claude-3-5-sonnet
GET /api/dashboard/filter-options   # → { departments: [...], providers: [...] }
```

The frontend filter bar (toggled via the Filters button) populates dropdowns from `/filter-options` and re-fetches all dashboard data on every filter change.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, TypeScript, Tailwind CSS, Recharts |
| Backend | FastAPI 0.115, Python 3.12+, SQLAlchemy 2, Pydantic v2 |
| Database | PostgreSQL 16 |
| Task Queue | Arq 0.25 (async worker, cron jobs, 3-retry policy) |
| Cache | Redis (integration status 15 s, dashboard overview 60 s) |
| Auth | JWT (python-jose) + RBAC (admin / reviewer / analyst / viewer) |
| Migrations | Alembic |
| Tests | pytest, savepoint-isolation against a real Postgres test DB; fakeredis for cache tests |
| Containerisation | Docker, docker-compose |

---

## Local Setup (no Docker)

**Prerequisites:** Python 3.11+, Node 18+, PostgreSQL running locally, **Redis running locally** (Phase 5).

```bash
# 1. Clone / enter project
cd tokenflow_ai

# 2. Create Postgres roles + databases
psql -U postgres -c "CREATE USER tokenflow WITH PASSWORD 'tokenflow';"
psql -U postgres -c "CREATE DATABASE tokenflow OWNER tokenflow;"
psql -U postgres -c "CREATE DATABASE tokenflow_test OWNER tokenflow;"

# 3. Generate synthetic data
python3 scripts/generate_synthetic_data.py

# 4. Install backend dependencies
cd backend && pip install -r requirements.txt

# 5. Apply migrations
python -m alembic upgrade head

# 6. Start backend
python -m uvicorn app.main:app --port 8000 --reload

# 7. Start arq background worker (new terminal — requires Redis)
cd backend && arq app.worker.settings.WorkerSettings

# 8. Start frontend (new terminal)
cd ../frontend && npm install && npm run dev
```

Open **http://localhost:3000/login** — default credentials: `admin@tokenflow.local` / `tokenflow2024`.

**Without Redis:** the app still works — sync endpoints degrade gracefully to showing "Redis unavailable" in the system status bar, and the Integrations page system bar shows `Redis disconnected`. Start Redis locally (`brew install redis && redis-server`) to unlock background workers, live polling, and caching.

Sync all connectors and generate recommendations from the **Integrations** page (admin only).

---

## Running Tests

```bash
cd backend
# Apply migrations to test DB first (one-time):
DATABASE_URL="postgresql://tokenflow:tokenflow@localhost:5432/tokenflow_test" python -m alembic upgrade head

# Run all tests
python -m pytest app/tests/ -v

# With coverage
python -m pytest app/tests/ --cov=app --cov-report=term-missing
```

Test count: **105 tests** across 6 test files.

---

## API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/health` | — | Health check |
| POST | `/api/auth/token` | — | Login (OAuth2 password flow) |
| GET | `/api/auth/me` | any | Current user |
| GET | `/api/auth/users` | admin | List users |
| POST | `/api/auth/users` | admin | Create user |
| POST | `/api/integrations/sync/{source}` | admin | Sync one connector (incremental) |
| POST | `/api/integrations/sync/all/run` | admin | Sync all connectors |
| GET | `/api/integrations/status` | any | Connector health + observability |
| GET | `/api/integrations/history` | any | Sync run history |
| GET | `/api/integrations/validation-logs` | any | Schema-drift warning log |
| GET | `/api/dashboard/overview` | any | KPI summary (filterable) |
| GET | `/api/dashboard/spend-over-time` | any | Daily spend series (filterable) |
| GET | `/api/dashboard/departments` | any | Per-department stats (filterable) |
| GET | `/api/dashboard/models` | any | Per-model stats (filterable) |
| GET | `/api/dashboard/filter-options` | any | Available filter values |
| GET | `/api/licenses/waste` | any | Inactive + duplicate seats |
| POST | `/api/recommendations/generate` | admin | Run recommendation engine |
| GET | `/api/recommendations` | any | List recommendations |
| PATCH | `/api/recommendations/{id}/review` | admin/reviewer | Accept / reject |
| GET | `/api/audit` | admin | Audit log |

Interactive docs: **http://localhost:8000/docs**

---

## Database Schema

```sql
users                    -- auth accounts (admin/reviewer/analyst/viewer)
employees                -- SSO identity roster
model_pricing            -- per-model token costs
ai_licenses              -- seat assignments + usage signal
ai_usage_events          -- normalised event table (api_gateway is authoritative)
browser_events           -- shadow AI + governance events
kafka_events             -- supplemental Kafka telemetry
clickhouse_aggregates    -- pre-aggregated ClickHouse rows
kubernetes_logs          -- K8s gateway pod metrics
recommendations          -- rule-based savings opportunities
integration_sync_runs    -- connector run history (watermark, duration, row counts)
ingestion_validation_logs -- per-row schema-drift warnings
audit_logs               -- full system action trail
```

---

## Production Upgrade Path

The MVP uses CSV/JSONL files to simulate real enterprise integrations. To connect to a live system, only the `_fetch_raw()` method of each connector needs to change — the normalization, UPSERT, watermark, and validation machinery stay the same.

| Connector | MVP source | Production replacement |
|---|---|---|
| **IdentityConnector** | `identity_directory.csv` | Okta `/api/v1/users`, Azure AD Graph API, or Google Workspace SCIM v2 |
| **ModelPricingConnector** | `model_pricing.csv` | Anthropic / OpenAI / Google pricing APIs or internal pricing DB |
| **LicenseInventoryConnector** | `ai_license_inventory.csv` | ChatGPT Enterprise admin API, GitHub Copilot seat management API |
| **APIGatewayConnector** | `api_gateway_traces.csv` | Envoy/Kong access log → ClickHouse; or direct PostgreSQL read from gateway DB |
| **BrowserExtensionConnector** | `browser_extension_events.csv` | Chrome extension background script → HTTPS POST `/api/telemetry/browser` with per-install JWT |
| **KafkaTelemetryConnector** | `kafka_ai_telemetry.jsonl` | Kafka consumer on topic `ai.telemetry.events` (confluent-kafka-python); each message maps to one row |
| **ClickHouseConnector** | `clickhouse_ai_traces.csv` | ClickHouse HTTP client: `SELECT ... WHERE timestamp > {since}` against `ai_request_traces` |
| **KubernetesLogsConnector** | `kubernetes_gateway_logs.csv` | Prometheus HTTP API (`/api/v1/query_range`) or `kubectl logs` pipe for the `ai-platform` namespace |
| **ProductivityConnector** | `productivity_metrics.csv` | GitHub REST API for commit/PR activity; Jira API for ticket throughput |

The `since` watermark passed to `connector.sync(since=dt)` translates to:
- ClickHouse: `WHERE timestamp > '{since}'`
- Kafka: consumer offset from the timestamp nearest to `since`
- Prometheus: `start` parameter on the range query
- REST APIs: `updated_since` / `after` query parameter

---

## Project Structure

```
tokenflow_ai/
├── scripts/
│   ├── generate_synthetic_data.py
│   └── dev_start.sh
├── synthetic-data/                  # CSV/JSONL files
├── docs/
│   └── migrations.md
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/                  # 13 SQLAlchemy models
│   │   ├── schemas/                 # Pydantic I/O schemas
│   │   ├── connectors/              # 9 connectors (CSV today, real APIs tomorrow)
│   │   ├── services/                # analytics, ingestion, licenses, recommendations
│   │   ├── api/                     # FastAPI route handlers
│   │   ├── core/                    # JWT security, RBAC dependencies
│   │   └── tests/                   # 105 tests across 6 files
│   ├── migrations/                  # Alembic revisions
│   └── requirements.txt
├── frontend/
│   ├── app/                         # Next.js App Router pages
│   ├── components/                  # Layout, cards, providers
│   ├── context/                     # UserContext (JWT + RBAC)
│   └── lib/                         # api.ts (auth-aware), auth.ts, utils.ts
├── docker-compose.yml
└── .env.example
```

---

## Async Architecture (Phase 5)

### Background Workers

Syncs are non-blocking. `POST /api/integrations/sync/{source}` enqueues an arq job and returns `{job_id, status: "queued"}` immediately. The arq worker executes the sync in the background and invalidates relevant Redis caches on completion.

```
POST /api/integrations/sync/api_gateway
→ {"source": "api_gateway", "job_id": "abc123", "status": "queued"}

GET /api/tasks/abc123
→ {"status": "in_progress", "start_time": "…"}   # poll until "complete"
```

Start the worker:
```bash
cd backend && arq app.worker.settings.WorkerSettings
```

Worker configuration (`app/worker/settings.py`):
- `max_jobs = 10` — up to 10 concurrent syncs
- `job_timeout = 300` — 5 min per sync before cancellation
- `max_tries = 3` — auto-retry on unhandled exception
- `keep_result = 600` — job result available in Redis for 10 min after completion
- Heartbeat cron runs every 15 min and on worker startup

### Redis Cache

| Key | TTL | Invalidated by |
|---|---|---|
| `integrations:status` | 15 s | Worker after each sync |
| `integrations:heartbeat:{source}` | 3600 s | Heartbeat cron |
| `dashboard:overview:{hash}` | 60 s | Worker after each sync |
| `dashboard:filter-options` | 300 s | Never (stable reference data) |

### Heartbeat Metrics

The heartbeat cron task checks every connector's data freshness (time since last successful sync) and stores the result in Redis. The Integrations page displays per-connector "Fresh / Stale / No data" badges populated from `GET /api/integrations/heartbeat` — which falls back to a live DB query if Redis isn't populated yet.

### Live Polling

The Integrations page auto-polls `/api/integrations/status` and `/api/integrations/activity` every 3 s when any connector reports `health: "syncing"`. Polling stops automatically when all connectors settle.

### New Endpoints (Phase 5)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/integrations/retry/{run_id}` | Re-enqueue a failed sync by run ID |
| GET | `/api/integrations/activity` | Recent sync event stream (newest first) |
| GET | `/api/integrations/heartbeat` | Per-connector data-freshness snapshot |
| GET | `/api/tasks/{job_id}` | Poll arq job status by ID |
| GET | `/api/system/status` | Redis connectivity, worker, active job count |

---

## Resume Bullets

- Built a full-stack enterprise AI governance platform (Next.js 16 + FastAPI + PostgreSQL) with JWT auth, RBAC (admin / reviewer / analyst / viewer), and 142-test pytest suite with savepoint-isolation
- Designed async connector orchestration with Arq background workers: non-blocking sync queue, 3-retry policy, 5-min job timeout, heartbeat cron, and Redis-backed caching (15 s–5 min TTLs)
- Implemented per-connector operational observability: live polling UI (3 s auto-refresh), activity feed, data-freshness heartbeat badges, retry-failed-run endpoint, and a system status bar surfacing Redis/queue/worker health
- Designed connector-based incremental ingestion: watermark-filtered UPSERT syncs, per-row schema-drift validation logs, and per-connector health states (healthy / degraded / failed / syncing / not_synced)
- Implemented a rule-based recommendation engine with SHA-256 deduplication — preserves in-flight investigations across re-runs, surfaces $760+/month in projected savings on synthetic data
- Added date/department/provider filter params across all dashboard analytics endpoints, backed by a composable `AnalyticsFilters` dataclass; results cached in Redis with filter-keyed TTLs
- Applied privacy-by-design: team-level analytics by default, no raw prompt storage, all write actions gated behind RBAC and logged to an immutable audit trail
