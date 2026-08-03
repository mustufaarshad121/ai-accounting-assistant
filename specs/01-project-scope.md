# 01 — Project Scope

## Purpose
Define exactly what the urgent MVP will and will not build, so implementation stays bounded and
every graded deliverable is covered.

## Requirement provenance (read this first)
Every item in these specs falls into exactly one of four categories. This prevents presenting our
implementation choices as though the assignment mandated them.

**1. Mandatory — directly stated in the assignment PDF**
- Full-stack web app + integrated AI service automating accountant/CA work.
- Manual **and** natural-language (AI) data entry.
- Reports generated from **real PostgreSQL data**, not hard-coded: P&L, balance sheet, a monthly
  audit/review, spending summaries, answering questions from the data.
- Stack: Next.js + TypeScript; Python managed with **uv**; FastAPI; **Pydantic for all
  request/response models**; **PostgreSQL**; a code-based agentic framework (developer's choice);
  Docker + docker-compose.
- Spec-Driven Development with a `/specs` folder; workflow diagram on **draw.io or Lucidchart**
  (shareable URL mandatory).
- GitHub feature branches, frequent small meaningful commits, PRs into main; README; AI chat history.
- Free-hosting deployment with a working live link at submission.

**2. Our design decisions (satisfy a mandatory requirement; the specific choice is ours)**
- **Supabase** as the PostgreSQL provider (Postgres is mandatory; the provider is our choice).
- **LangGraph** as the agentic framework (a framework is mandatory; which one is our choice —
  justified in the research paper).
- Configurable **OpenAI-compatible** model endpoint via `LLM_*` env vars (model is developer's choice).
- **Double-entry accounting** with a chart of accounts, journal entries/lines, and derived views
  instead of separate `daily_expenses`/`income` source tables — chosen so all reports reconcile.
- **Trial Balance** — not named in the PDF; included because it validates that double-entry data is
  internally consistent (debits = credits) before P&L/Balance Sheet are trusted.
- **"Automated Monthly Accounting Review"** — our name for the PDF's requested "monthly audit."
  It fulfils that capability but is explicitly **not** a statutory or external audit opinion.
- `DRAFT/POSTED/REVERSED` statuses, reversal-instead-of-delete, and the seven named transaction
  flows — our modeling of standard bookkeeping practice.
- Render/Railway for the backend, Vercel for the frontend — permitted free-hosting choices.

**3. Deferred because of the urgent deadline (allowed, not now)**
- **Authentication** — the PDF does **not** require it. Deferred entirely for the MVP. If added later:
  Supabase Auth email/password sign-up/in/out, protected routes, FastAPI token validation only.
  The `profiles` table schema is prepared but unused until then.
- Cash-flow statement and tax-summary views (research paper covers them; not built in MVP).

**4. Future improvements (out of scope — roadmap/research only)**
See "Out of scope" below. These appear only in the research paper and future-roadmap sections and
must never be presented as assignment requirements.

## In scope (MVP)
**Accounting core (double-entry)**
- Chart of accounts (default seed, 5 account types).
- Journal entries + journal lines with `DRAFT / POSTED / REVERSED` status and
  `MANUAL / AI / SYSTEM / IMPORT` source.
- Balanced-entry enforcement (debits = credits) — backend rejects unbalanced.
- Seven transaction flows: owner investment, cash income, cash expense, vendor bill,
  vendor payment, owner withdrawal, fund transfer.
- Safe update (drafts editable) + reversal of posted entries (no hard delete).

**Derived views (NOT source tables)**
- Daily expenses, monthly office expenses, income, ledger — all derived from
  accounts + journal lines + dates + filters. Search/filter over entries.

**Reports (deterministic Python, real data)**
- Trial Balance, Profit & Loss, Balance Sheet, Automated Monthly Accounting Review.

**AI agent (one LangGraph agent)**
- Natural-language income/expense/other entries via approved tools only.
- Clarification before writing when accounting-relevant info is missing.
- Preview/confirmation before post/update/reverse.
- Spending questions ("How much on utilities in March?").

**Frontend (Next.js + TS + App Router + Tailwind)**
- Pages: dashboard, accounts, entries, entries/new, expenses/daily, expenses/monthly,
  income, ledger, reports/{trial-balance,profit-loss,balance-sheet,monthly-review}, assistant.
- Loading / empty / validation / error / success states; date filters; search; responsive.

**Ops**
- Docker + docker-compose (postgres + backend + frontend). Alembic migrations.
- Deployment plan: Vercel (frontend), Render/Railway (backend), Supabase Postgres (db).

## Out of scope (future improvements only)
Firebase; receipt/invoice OCR; real bank feeds/reconciliation; payment processing; payroll;
inventory; tax filing; multi-company; multi-currency; PO matching; complex approvals; ML fraud
detection; advanced forecasting; formal audit opinions; complex auth; RBAC.

## Authentication decision
Not in initial priority. **No Firebase.** Supabase Postgres used immediately as the DB.
Supabase Auth (email/password sign-up, sign-in, sign-out, protected routes, FastAPI token
validation) only **after** core flow + reports + AI + Docker + deployment work. `profiles` table
schema is prepared but may stay unused until then.

## Definition of done (MVP)
Thin end-to-end slice works first: AI (or form) creates a balanced expense → PostgreSQL → visible
in ledger UI. Then all reports compute from real data; monthly review produces findings; all
required API routes exist with Pydantic models; Docker one-command run; deployment documented.

## Inputs / Outputs / Validation / Edge cases / Acceptance
- **Inputs:** user forms + natural-language chat + report date filters.
- **Outputs:** persisted balanced journal entries; deterministic report JSON; agent messages.
- **Validation:** Pydantic on every request/response; debits = credits; valid accounts/dates/amounts.
- **Edge cases:** see `09-edge-cases.md`.
- **Acceptance:** see `10-acceptance-criteria.md`.
