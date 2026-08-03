# Implementation Plan

Urgent MVP build order. Each priority band maps to a feature branch (see Git strategy below) and to
acceptance criteria in `specs/10-acceptance-criteria.md`. **Specs are frozen before code** per SDD.

> Deadline note: the assignment PDF states the original deadline of **29 July 2026**. The candidate
> reports receiving a **separate updated deadline**, which must be verified from the employer's written
> communication before it is relied upon (no such written evidence exists in this repo yet). This plan
> proceeds as an urgent MVP regardless. See `specs/00-assignment-requirements.md` for the authoritative note.

## Priority 1 — Research & specs (branch `docs/research-specs`)
- [x] Read assignment PDF; summarize mandatory requirements (`specs/00`).
- [x] Write all 12 specs (`specs/00`–`specs/11`).
- [x] Research-paper outline (`docs/research-paper-outline.md`).
- [x] Workflow-diagram content (`docs/workflow-diagram-content.md`).
- [x] Testing / deployment / submission checklists + AI-chat-history templates + CLAUDE.md.
- [ ] **Approval gate:** human approves specs before any application code.

## Priority 2 — Scaffold + accounting core (branch `chore/project-scaffold`, then `feature/accounting-core`)
- Scaffold FastAPI (uv) + Next.js (TS, App Router, Tailwind).
- SQLAlchemy 2 models + Alembic initial migration (enums + tables per `specs/03`).
- Seed default chart of accounts.
- `AccountingService`: build lines from templates, enforce balance, entry numbering, post.
- Endpoints: accounts (GET/POST), entries (GET list/detail), income + expense create.
- Reject unbalanced entries.

## Priority 3 — Thin end-to-end slice (part of `feature/accounting-core` / `feature/frontend`)
- Next.js New Entry form → FastAPI → service → Postgres → ledger list renders it.
- Loading / empty / error / success states on this path.

## Priority 4 — Reports (branch `feature/reports`)
- Remaining entry endpoints (owner-capital, vendor-bill, vendor-payment, owner-withdrawal, transfer,
  PATCH, reverse).
- `ReportService`: Trial Balance → P&L → Balance Sheet.
- `ReviewService`: Automated Monthly Accounting Review (deterministic rules + severities).

## Priority 5 — AI agent (branch `feature/ai-agent`)
- LangGraph single agent; approved tools wrapping the same services; Pydantic tool args.
- Clarification + preview/confirmation rules (`specs/06`).
- `POST /assistant/chat`, `GET /assistant/threads/{id}`; log tool calls.
- AI-created income + expense; spending questions.

## Priority 6 — Frontend, Docker, deploy, tests, docs (branches `feature/frontend`, `chore/docker-deployment`)
- All pages in `specs/01`; date filters, search, responsive.
- Dockerfiles + docker-compose (postgres + backend + frontend); `.dockerignore`.
- Backend tests (`docs/testing-plan.md`); frontend checks; mocked model for agent tests.
- Deploy Vercel + Render/Railway + Supabase; README with completion-status disclosure.

## Git strategy
Branches: `docs/research-specs`, `chore/project-scaffold`, `feature/accounting-core`,
`feature/reports`, `feature/ai-agent`, `feature/frontend`, `chore/docker-deployment`.
Small meaningful commits; PR per branch into `main`. No single giant commit.
Before any branch/commit/push/PR, the command + purpose is reported to the human first.

## Risks / mitigations
- **Deadline** → original PDF date is 29 Jul 2026; updated deadline unverified → verify in writing, proceed as MVP.
- **LLM cost/availability** → configurable endpoint; mocked responses in tests.
- **Supabase connection modes** → pooled URL for app, direct URL for Alembic.
- **Scope creep** → "Do not implement now" list in `specs/01`; extras are future work only.
