# AI-Powered Accounting & Finance Assistant

A full-stack, double-entry accounting web application with an integrated AI
assistant. An office admin or business owner manages financial records
(income, expenses, ledgers) through a modern web UI **and** through natural
language, while an AI agent automates routine accountant/CA tasks.

> **Assignment purpose.** Build a full-stack app + integrated AI service that
> automates day-to-day accounting work, using Spec-Driven Development. Reports
> are generated from **real PostgreSQL data** (never hard-coded). See
> [`specs/00-assignment-requirements.md`](specs/00-assignment-requirements.md)
> for the authoritative requirements.

---

## Current status: **Project Scaffold**

This branch (`chore/project-scaffold`) establishes the foundation only. **No
accounting features exist yet.**

### Completed in this phase
- Next.js (TypeScript, App Router, Tailwind, ESLint, `src/`) frontend scaffold.
- Typed API client + health-check service reading `NEXT_PUBLIC_API_URL`.
- Minimal landing page showing live **Backend connected / unavailable** status.
- FastAPI backend managed with **uv**: Pydantic settings, CORS, structured
  errors, async SQLAlchemy 2 engine/session foundation, Alembic foundation.
- `GET /health` endpoint with a Pydantic response model (no DB dependency).
- Backend health test (pytest).
- Local Docker Compose stack (postgres + backend + frontend).

### Pending (later branches)
- Accounts, journal entries/lines, chart-of-accounts seed, Alembic migrations.
- Accounting services + entry endpoints; reports (Trial Balance, P&L, Balance
  Sheet, Automated Monthly Accounting Review).
- LangGraph AI agent + approved tools.
- Accounting frontend screens (dashboard, entries, ledger, reports, assistant).
- Deployment (Vercel + Render/Railway + Supabase).

### Known limitations
- No authentication (out of scope for the MVP; `profiles` schema prepared only).
- No database schema/tables yet — the app boots without a live database, and
  `GET /health` intentionally does **not** require one.
- Docker was **not** built/run in the authoring environment (Docker not
  installed there); the compose file and Dockerfiles are provided and YAML/
  structure-validated but have not been exercised via `docker compose build`.

---

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | Next.js (App Router), TypeScript, Tailwind CSS, ESLint |
| Backend | Python (managed with **uv**), FastAPI |
| Validation | Pydantic (all request/response models) |
| ORM / Migrations | SQLAlchemy 2 (async) / Alembic |
| Database | PostgreSQL (Supabase in deployment; local Postgres via Docker) |
| AI framework | LangGraph (single agent) — *later branch* |
| Containers | Docker + Docker Compose |
| Deploy | Vercel (frontend), Render/Railway (backend), Supabase (DB) — *later* |

## Architecture summary

Next.js UI → FastAPI (`/api/v1`, thin routes) → service layer (double-entry
posting, balance enforcement, reports) → PostgreSQL (SQLAlchemy 2 + Alembic).
The AI agent calls **only approved, Pydantic-typed tools** that delegate to the
same services the REST API uses; it never touches SQL and never computes
financial totals. Full detail in
[`specs/02-system-architecture.md`](specs/02-system-architecture.md).

## Repository structure

```
.
├── backend/            FastAPI app (uv-managed)
│   ├── app/
│   │   ├── api/routes/  health route (thin routers)
│   │   ├── agent/       AI agent (later)
│   │   ├── core/        config, structured errors
│   │   ├── db/          async engine/session + declarative base
│   │   ├── models/      ORM models (later)
│   │   ├── reports/     report services (later)
│   │   ├── schemas/     Pydantic schemas
│   │   ├── services/    business logic (later)
│   │   ├── tests/       pytest suite
│   │   └── main.py      app factory
│   ├── migrations/      Alembic (no revisions yet)
│   ├── alembic.ini
│   └── pyproject.toml
├── frontend/           Next.js app
│   └── src/{app,components,config,lib,services,types}
├── docs/               plans, checklists, AI chat history
├── specs/              Spec-Driven Development specs (00–11)
├── docker-compose.yml
└── CLAUDE.md           permanent project rules
```

## Prerequisites
- **Node.js** 20+ and npm (frontend).
- **uv** (backend Python/dependency manager; installs its own Python 3.13).
- **Docker + Docker Compose** (optional, for the one-command local stack).

---

## Frontend setup

```bash
cd frontend
npm install
cp .env.example .env.local   # sets NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                  # http://localhost:3000
```

Checks:

```bash
npm run lint
npm run build
```

## Backend setup (uv)

```bash
cd backend
uv sync
cp .env.example .env         # local dev placeholders only — never commit real secrets
uv run uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs for the OpenAPI UI.

## Environment setup

Copy the example files and edit locally. Example files contain **placeholders
only**; real values live in git-ignored `.env` / `.env.local` files.

- `frontend/.env.example` → `frontend/.env.local`
  - `NEXT_PUBLIC_API_URL` — backend base URL (browser-exposed).
- `backend/.env.example` → `backend/.env`
  - `DATABASE_URL` — pooled **async** URL (`postgresql+asyncpg://…`) for the app.
  - `DIRECT_DATABASE_URL` — direct URL for Alembic migrations.
  - `FRONTEND_URL` — CORS allowed origin.
  - `ENVIRONMENT` — e.g. `development`.

## Docker Compose

One command brings up Postgres + backend + frontend:

```bash
docker compose up --build
```

- Frontend → http://localhost:3000
- Backend → http://localhost:8000 (docs at `/docs`)
- Postgres → localhost:5432 (db `accounting_assistant`, user `postgres`)

The Postgres credentials in `docker-compose.yml` are **local development only**
and must never be reused for Supabase or production. No tables are created at
startup; schema is applied later via Alembic.

## `GET /health`

Liveness endpoint; does **not** require a database connection.

```bash
curl http://localhost:8000/health
```

```json
{ "status": "ok", "service": "ai-accounting-assistant-api" }
```

## Supabase strategy

PostgreSQL is mandatory; **Supabase** is the chosen provider for deployment.
- App runtime uses the **pooled** connection (`DATABASE_URL`, asyncpg).
- Alembic migrations use the **direct** connection (`DIRECT_DATABASE_URL`).
- Server-side secrets (e.g. a Supabase secret key) are used on the backend only
  and never shipped to the browser. Only `NEXT_PUBLIC_*` vars reach the client.
- During this scaffold phase Supabase is used read-only for verification; no
  tables, migrations, or writes have been created.

## Secret-management warning

> **Never commit real secrets.** `.env` / `.env.local` are git-ignored; only
> `.env.example` (placeholders) is tracked. Do not paste API keys, passwords,
> tokens, or connection strings into code, docs, commits, or chat history. The
> Docker Compose credentials are throwaway local-dev values only.

## Testing commands

```bash
# Backend
cd backend
uv run ruff check .
uv run pytest

# Frontend
cd frontend
npm run lint
npm run build
```

---

## Workflow diagram

_Placeholder._ A draw.io / Lucidchart workflow diagram (user flows, AI agent
flow, data flow) will be added with a shareable URL and a repo export.
Planned content: [`docs/workflow-diagram-content.md`](docs/workflow-diagram-content.md).

## Research paper

_Placeholder._ The research paper (accountant/CA tasks, AI automation,
agentic-framework comparison, model choice, architecture, feature list) will be
added as a PDF. Outline: [`docs/research-paper-outline.md`](docs/research-paper-outline.md).

## Deadline note

The assignment PDF states an original deadline of **Wednesday, 29 July 2026**. A
separate updated deadline has been reported but is **not** verified in this
repository (no written evidence committed). All work proceeds as an urgent MVP
regardless. See [`specs/00-assignment-requirements.md`](specs/00-assignment-requirements.md).

## Next branch

`feature/accounting-core` — database models, Alembic initial migration,
chart-of-accounts seed, accounting services, and the first entry endpoints.
