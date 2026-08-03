# Deployment Checklist

Mirrors `specs/11-deployment-specification.md`. Check each box during the deployment pass.

## Pre-deploy
- [ ] All backend tests pass locally (`uv run pytest`).
- [ ] `docker compose up --build` runs Postgres + backend + frontend cleanly.
- [ ] `.env.example` present; real `.env` git-ignored; no secrets committed.
- [ ] Alembic migrations up to date; seed script ready.

## Supabase (database)
- [ ] Create Supabase project.
- [ ] Copy pooled connection → `DATABASE_URL` (app runtime).
- [ ] Copy direct connection → `DIRECT_DATABASE_URL` (Alembic).
- [ ] Run `alembic upgrade head` against direct URL.
- [ ] Seed default chart of accounts; verify 18 accounts exist.

## Backend (Render / Railway)
- [ ] Deploy FastAPI service.
- [ ] Set env: `DATABASE_URL`, `DIRECT_DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY`,
      `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `FRONTEND_URL`, `ENVIRONMENT`.
- [ ] `GET /health` returns healthy (DB connectivity ok).
- [ ] `/docs` (OpenAPI) reachable.

## Frontend (Vercel)
- [ ] Deploy Next.js app.
- [ ] Set `NEXT_PUBLIC_API_URL` = live backend URL.
- [ ] Set `SUPABASE_URL` / `SUPABASE_PUBLISHABLE_KEY` if used client-side (later/auth phase).
- [ ] App loads; no console errors on core pages.

## Wire-up
- [ ] Backend CORS `FRONTEND_URL` = Vercel domain.
- [ ] AI env vars set on backend; assistant responds.

## Live verification
- [ ] Create a transaction via AI assistant on the live app.
- [ ] Refresh; confirm the entry persisted.
- [ ] Create a manual entry via the form; appears in ledger.
- [ ] Generate Trial Balance, P&L, Balance Sheet from production data.
- [ ] Run Automated Monthly Accounting Review; findings render.

## Post-deploy
- [ ] README updated with live links + completion-status disclosure.
- [ ] Workflow diagram public URL added to README.
- [ ] Research paper PDF committed / linked.
