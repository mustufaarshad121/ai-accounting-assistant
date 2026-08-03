# 02 — System Architecture

## Purpose
Describe components and how a request flows from UI → API → agent → services → database → response.

## Components
- **Frontend** — Next.js (App Router) + TypeScript + Tailwind. Server/client components call the
  backend over `NEXT_PUBLIC_API_URL`. No business logic; no hard-coded totals.
- **API** — FastAPI, versioned under `/api/v1`. Routes are thin; they validate with Pydantic and
  delegate to service functions/classes.
- **Pydantic validation layer** — request/response models; rejects malformed input before services.
- **Accounting services** — double-entry posting, balance enforcement, reversal, entry numbering.
- **Report services** — Trial Balance, P&L, Balance Sheet, Monthly Review. Pure, deterministic,
  read-only aggregations over journal lines.
- **LangGraph agent** — single agent; calls **approved tools only**; never touches SQL directly.
- **Approved agent tools** — thin wrappers that call the same accounting/report services the API
  uses (single source of truth), with structured Pydantic arguments.
- **Database** — Supabase PostgreSQL via SQLAlchemy 2 + Alembic. Money stored as `NUMERIC`.

## Request flows
**Manual entry:** UI form → `POST /api/v1/entries/{type}` → Pydantic → accounting service →
balance check → persist (source=MANUAL, status=POSTED) → response → UI refresh.

**AI entry:** UI chat → `POST /api/v1/assistant/chat` → LangGraph agent → (clarify if needed) →
preview → on confirm, approved tool → accounting service → persist (source=AI) → agent states
operation, debits, credits, amount, date, entry number → UI.

**Report:** UI → `GET /api/v1/reports/{report}` (+date filters) → Pydantic query params → report
service aggregates journal lines → deterministic totals → response → UI renders (never recomputes).

**Monthly review:** UI/agent → `GET /api/v1/reports/monthly-review` → review service runs
deterministic rule checks → findings with severity → optional AI summary of findings.

**Error/validation:** any invalid input → Pydantic/service raises → API returns structured error
(422/400/404/409) → UI shows validation/error state.

## Cross-cutting
- **Single source of truth:** API routes and agent tools both call the same services — the LLM never
  computes financial totals and never sees raw SQL.
- **Config:** `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` (OpenAI-compatible); DB URLs; CORS via
  `FRONTEND_URL`. See `.env.example`.
- **CORS:** backend allows the deployed frontend origin.

## Deployment topology
Vercel (Next.js) → Render/Railway (FastAPI) → Supabase PostgreSQL. Local: docker-compose runs
postgres + backend + frontend. See `11-deployment-specification.md`.

## Inputs/Outputs/Validation/Errors/Edge/Acceptance
- Inputs: HTTP requests, chat messages, env config. Outputs: JSON responses, persisted rows.
- Validation: Pydantic + service invariants. Errors: structured HTTP errors.
- Edge: agent tool failure surfaces as a normal error message, no partial writes.
- Acceptance: `10-acceptance-criteria.md`.
