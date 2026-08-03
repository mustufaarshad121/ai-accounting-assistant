# 10 — Acceptance Criteria

Definition of done for the MVP. Each item is objectively checkable and maps to tests or a manual demo
step. Grouped by priority band (see `docs/implementation-plan.md`).

## Priority 2 — Accounting core
- [ ] Default chart of accounts (all codes in `04-accounting-rules.md`) seeded on init.
- [ ] `POST /api/v1/entries/income` and `/expense` create balanced POSTED entries and persist.
- [ ] Posting a **balanced** entry succeeds; the resulting entry has a unique `entry_number`.
- [ ] Posting an **unbalanced** entry returns 422/400 and commits nothing.
- [ ] `GET /api/v1/entries` lists entries; `GET /api/v1/entries/{id}` returns lines.
- [ ] Money stored as `NUMERIC(…,2)`; no float column for money.

## Priority 3 — Thin end-to-end slice
- [ ] A user submits the New Entry form in Next.js → FastAPI → service → PostgreSQL → the entry
      appears in the ledger view. (Manual demo + one integration check.)
- [ ] Frontend shows loading, empty, error, and success states on that flow.

## Priority 4 — Reports
- [ ] Trial Balance: `total_debit == total_credit` for any seeded balanced dataset.
- [ ] P&L: `net_profit == total_revenue − total_expenses`; per-account groups sum to totals.
- [ ] Balance Sheet: `Assets == Liabilities + Equity` on all seeded scenarios; equity includes
      capital − drawings + current-period earnings.
- [ ] Monthly Review: each rule in `07` triggers its finding with correct severity on a seeded case.
- [ ] No report value is hard-coded; all derive from DB.

## Priority 5 — AI agent
- [ ] Agent creates an income entry and an expense entry via natural language (mocked model in tests).
- [ ] Agent asks for missing info ("Add office rent 50,000" → asks date + cash/bank/payable) and does
      **not** write until provided.
- [ ] Agent shows a preview and requires confirmation before posting/updating/reversing.
- [ ] Confirmed AI write produces an entry with `source=AI` and the response states operation, debit
      account, credit account, amount, date, and entry number.
- [ ] "How much did we spend on utilities in March?" returns a figure sourced from a deterministic
      service, not model arithmetic.
- [ ] Every tool call is recorded in `agent_tool_calls`.

## Priority 6 — Frontend / Docker / deploy / tests / docs
- [ ] All routes in `01-project-scope.md` render with loading/empty/error/success + date filter/search
      where applicable; responsive; no hard-coded totals.
- [ ] `docker compose up --build` starts Postgres + backend + frontend; frontend :3000, backend :8000,
      docs at :8000/docs.
- [ ] `GET /health` returns healthy (and reports DB connectivity).
- [ ] Backend tests in `docs/testing-plan.md` pass; agent tests use mocked model responses.
- [ ] README complete with completion-status disclosure (done / partial / pending).
- [ ] Deployed frontend (Vercel) talks to deployed backend (Render/Railway) on Supabase; live link
      works; data persists across refresh.

## Cross-cutting
- [ ] `.env.example` present with placeholders only; no real secret committed.
- [ ] Specs precede code; work on feature branches with small commits and PRs.
