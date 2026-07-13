# Nudge — Explainable Financial Early-Warning System

Nudge forecasts where your spending will land by month-end, catches
changes in your habits before they become a problem, explains what's
driving the risk, and recommends a concrete action — then tracks whether
you took it and whether it helped.

This repo is a full-stack monorepo: a FastAPI backend and a Next.js
frontend, built to run locally with **zero API keys** (every external
integration has a realistic mock fallback) and to deploy cleanly once you
add real credentials.

> **Scope note:** price-tracking and local-deals were part of an earlier,
> broader version of this project. They're cut from the active product —
> code still exists (`app/api/price_watches.py`, `app/api/deals.py`,
> `frontend/app/price-watch/`, `frontend/app/deals/`) but isn't registered
> in the API router or linked in navigation. The product is deliberately
> narrower now: forecasting, anomaly/risk detection, budgeting, and a
> grounded chat interface into all three.

## How mock mode works

Every external dependency — Plaid, Anthropic Claude, Supabase, SendGrid —
is wrapped in a service class that checks whether its API key is set. If
not, it returns deterministic, realistic mock data instead of failing.
This means:

- You can clone this repo, run `docker-compose up`, and have a fully
  working app with synthetic transactions, a forecast, anomaly alerts,
  and an AI-sounding budget, before you've signed up for anything.
- As you get real API keys, drop them into `backend/.env` and each
  feature individually switches from mock to live — no code changes needed.
- `GET /health` tells you which integrations are currently mocked.

## Architecture

```
nudge/
├── backend/                  FastAPI + Celery (Python 3.12)
│   ├── app/
│   │   ├── api/               Route handlers, one file per resource
│   │   ├── core/               config.py (settings/env), security.py (auth + encryption)
│   │   ├── db/                 SQLAlchemy async engine/session
│   │   ├── models/             SQLAlchemy ORM models
│   │   ├── schemas/             Pydantic request/response schemas
│   │   ├── services/            External integrations (Plaid, Claude)
│   │   ├── ml/                  Prophet forecasting, Isolation Forest anomaly detection, evaluation/ harnesses
│   │   ├── tasks/               Celery app + background jobs (sync, scans, emails)
│   │   └── main.py               App entrypoint
│   ├── migrations/             Alembic migrations (incl. TimescaleDB hypertable setup)
│   ├── scripts/                 Dev helpers: gen_key.py, seed_dev_data.py, run_*_evaluation.py
│   ├── tests/                   Pytest suite
│   ├── requirements.txt
│   ├── Dockerfile / Dockerfile.worker
│   └── .env.example
├── frontend/                  Next.js 14 (App Router) + TypeScript
│   ├── app/                     One folder per route (page.tsx)
│   ├── components/              Shared UI (Sidebar, Card, BufferRing, PageHeader)
│   ├── lib/                      api.ts (typed fetch client), format.ts
│   ├── store/                    Zustand store
│   ├── types/                    Shared TypeScript types mirroring backend schemas
│   ├── Dockerfile
│   └── .env.example
├── docker-compose.yml         Orchestrates Postgres/Timescale, Redis, backend, worker, beat, frontend
└── .github/workflows/ci.yml   Tests backend, builds frontend, builds Docker images
```

### Tech stack

| Layer | Choice |
|---|---|
| Backend | FastAPI, SQLAlchemy 2.0 (async), Alembic, Celery |
| Database | PostgreSQL + TimescaleDB (transactions table is a hypertable) |
| Queue/cache | Redis |
| Auth | Supabase Auth (JWT verification); falls back to a single dev user locally |
| AI | Anthropic Claude — categorization, budget reasoning, chat, anomaly explanations, price verdicts |
| ML | Prophet (spend forecasting), scikit-learn Isolation Forest (anomaly detection) |
| Bank data | Plaid (transactions, accounts) |
| Frontend | Next.js 14 App Router, TypeScript, Tailwind, Recharts, Zustand |

## Quickstart (Docker, recommended)

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Generate a real encryption key for Plaid tokens (do this even in mock mode)
python3 backend/scripts/gen_key.py
# paste the output into backend/.env as TOKEN_ENCRYPTION_KEY

docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend docs: http://localhost:8000/docs
- Health/mock-mode status: http://localhost:8000/health

The backend container runs Alembic migrations automatically on startup. To seed realistic mock data (a dev user, a linked mock bank, 90 days of transactions):

```bash
docker-compose exec backend python scripts/seed_dev_data.py
```

## Quickstart (without Docker)

**Backend**
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in TOKEN_ENCRYPTION_KEY at minimum
alembic upgrade 0001_initial   # use 'head' instead if your Postgres has TimescaleDB enabled
python scripts/seed_dev_data.py
uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

**Celery (optional locally — only needed for background sync/scans/emails)**
```bash
celery -A app.tasks.celery_app worker --loglevel=info
celery -A app.tasks.celery_app beat --loglevel=info
```

## TimescaleDB note

Migration `0002_timescale` converts `transactions` into a TimescaleDB hypertable for efficient time-range queries at scale. This requires the `timescaledb` extension:

- **Supabase**: enable it under Database → Extensions → `timescaledb`.
- **Self-hosted / Docker**: already handled — `docker-compose.yml` uses the `timescale/timescaledb-ha` image.
- **Plain Postgres** (no Timescale): skip migration `0002` and stay on `0001_initial`. The app works identically on plain Postgres; you just lose hypertable chunking benefits at very large data volumes.

## Prophet / forecasting note

Prophet's forecasting backend (`cmdstan`) needs a one-time compiled-binary install that requires a C++ toolchain and can take several minutes. If it's not installed, the forecasting module **automatically falls back** to a moving-average projection with confidence bands — the `/forecast` endpoint never fails, it just gets less sophisticated without Prophet. To enable full Prophet forecasting in your deploy image, uncomment the `cmdstanpy.install_cmdstan()` line in `backend/Dockerfile`.

## Connecting real services

Each integration becomes "live" the moment its key is present in `backend/.env`:

| Service | Env vars | Used for |
|---|---|---|
| Plaid | `PLAID_CLIENT_ID`, `PLAID_SECRET`, `PLAID_ENV` | Bank linking, transaction sync |
| Anthropic | `ANTHROPIC_API_KEY` | Categorization, AI budgets, chat, anomaly context, price verdicts |
| Supabase | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` | Auth, hosted Postgres |
| Google Places / Yelp / Eventbrite | `GOOGLE_PLACES_API_KEY` / `YELP_FUSION_API_KEY` / `EVENTBRITE_API_TOKEN` | Local deals feed |
| CamelCamelCamel | `CAMELCAMELCAMEL_API_KEY` | Price history (falls back to a lightweight page scraper, then to synthetic history) |
| SendGrid | `SENDGRID_API_KEY` | Weekly pulse emails |

## Deploying

- **Backend**: any container host (Render, Railway, Fly.io, ECS). Build from `backend/Dockerfile`; run migrations with `alembic upgrade head` as a release step; run `Dockerfile.worker` as a second service for Celery, plus a `celery beat` process for the schedule.
- **Frontend**: Vercel is the path of least resistance for Next.js (just set `NEXT_PUBLIC_API_URL`). The included `frontend/Dockerfile` (standalone output) also works on any container host.
- **Database**: Supabase is the natural fit (Postgres + Auth + Timescale extension in one place), but any managed Postgres works if you handle auth separately.

## Known tradeoffs (read before shipping to real users)

- **Next.js dependency advisories**: pinned to `14.2.35` (patched for the Dec 2025 advisory). A few additional advisories in the Next.js 14→16 range are only resolved by a major-version upgrade to Next 16, which changes App Router conventions enough that it's left as a deliberate followup rather than bundled here.
- **Non-negotiable categories** in AI budget generation are currently hardcoded (`Utilities & Bills`, `Health & Fitness`) rather than user-configurable — straightforward to expose as a settings field.
- **Plaid webhooks** aren't implemented; transaction sync is pull-based (manual sync button + nightly Celery job) rather than push-based. Fine for an MVP/portfolio context; real-time sync would add a webhook receiver endpoint.
- **Single dev user in mock auth mode**: until `SUPABASE_JWT_SECRET` is set, every request resolves to one fixed UUID. This is intentional for local development but means there's no real multi-user isolation until Supabase auth is wired up.

## Testing

```bash
cd backend
pytest tests/ -v
```

Covers: health check, Claude service mock-mode logic (categorization, budgeting, price verdicts), Plaid mock-mode data generation, and the ML fallback paths (forecasting cold-start, anomaly detection on small datasets).

```bash
cd frontend
npm run build   # type-checks and builds all 10 routes
```
