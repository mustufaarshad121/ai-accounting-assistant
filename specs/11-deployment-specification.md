# 11 — Deployment Specification

## Targets
- **Frontend:** Vercel (Next.js).
- **Backend:** Render or Railway (FastAPI, container or native Python via uv).
- **Database:** Supabase PostgreSQL (production).
- **Local:** Docker Compose (Postgres + backend + frontend).

## Environments & variables
See `.env.example`. Server-side only: `DATABASE_URL`, `DIRECT_DATABASE_URL`, `SUPABASE_URL`,
`SUPABASE_SECRET_KEY`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `FRONTEND_URL`, `ENVIRONMENT`.
Client-exposed: `NEXT_PUBLIC_API_URL`, `SUPABASE_PUBLISHABLE_KEY`.
- `DATABASE_URL` = pooled connection (app runtime). `DIRECT_DATABASE_URL` = direct connection (Alembic
  migrations). Both from Supabase.

## Local (Docker Compose)
- Services: `db` (postgres:16), `backend` (FastAPI, depends_on db, runs migrations then uvicorn),
  `frontend` (Next.js, depends_on backend).
- One command: `docker compose up --build`.
- URLs: frontend http://localhost:3000, backend http://localhost:8000, docs http://localhost:8000/docs.

## Production deployment order
1. Create Supabase project; get pooled + direct connection strings.
2. Configure backend env with `DATABASE_URL` / `DIRECT_DATABASE_URL`.
3. Run Alembic migrations against Supabase (`alembic upgrade head`) + seed chart of accounts.
4. Deploy FastAPI to Render/Railway; set all server env vars.
5. Verify `GET /health` (and DB connectivity) on the live backend.
6. Deploy Next.js to Vercel.
7. Set `NEXT_PUBLIC_API_URL` on Vercel to the live backend URL.
8. Set backend CORS `FRONTEND_URL` to the Vercel domain.
9. Set AI env vars (`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`) on the backend.
10. Create a transaction via the AI assistant on the live app.
11. Refresh the app; confirm the entry persisted.
12. Generate Trial Balance / P&L / Balance Sheet from production data.

## Migrations
- Alembic is the single source of schema truth. Never edit the DB by hand in production.
- Migrations run against `DIRECT_DATABASE_URL`. App runtime uses pooled `DATABASE_URL`.

## Health & observability
- `GET /health`: returns `{status, db: ok|error}`; used by platform health checks.
- Structured logs for API errors and every agent tool call; never log secrets.

## Rollback
- Frontend: redeploy previous Vercel build.
- Backend: redeploy previous image/commit.
- DB: forward-fix via new Alembic migration (avoid destructive down-migrations in prod).

## Acceptance
- `docker compose up --build` yields a working local stack (all three URLs).
- Live frontend reaches live backend; AI-created entry persists across refresh; reports compute from
  production data. Deadline note (`00`) tracked in README status.
