# Submission Checklist

Maps to the six deliverables in the assignment PDF (Section 5) plus GitHub/version-control rules.

## Deliverable 1 — Live deployment link
- [ ] Frontend (Vercel) live and connected to backend + Supabase DB.
- [ ] Backend (Render/Railway) live; `/health` ok; `/docs` reachable.
- [ ] Data persists across refresh; reports compute from production data.

## Deliverable 2 — Research paper (PDF)
- [ ] 6–15 pages, own writing, defensible in review.
- [ ] Covers all 28 topics in `docs/research-paper-outline.md` (CA tasks, AI automation mapping,
      framework comparison + LangGraph justification, model selection, architecture, feature scope,
      future work, controls, references).
- [ ] References are real (no fabricated sources); market-fact items flagged via research checklist.
- [ ] Exported to PDF and committed / linked.

## Deliverable 3 — Workflow diagram URL
- [ ] Diagram built in draw.io or Lucidchart using `docs/workflow-diagram-content.md`.
- [ ] All required nodes + 6 flows present.
- [ ] Public/shareable URL added to README.
- [ ] PNG/PDF export committed to repo.

## Deliverable 4 — GitHub repository
- [ ] Public / shared-access; URL submitted.
- [ ] Feature branches used (`docs/research-specs`, `chore/project-scaffold`,
      `feature/accounting-core`, `feature/reports`, `feature/ai-agent`, `feature/frontend`,
      `chore/docker-deployment`).
- [ ] Small meaningful commits; merged via PRs; no single giant commit.
- [ ] Contains README, `/specs`, workflow diagram export, Docker setup.

## Deliverable 5 — Docker setup
- [ ] `frontend/Dockerfile`, `backend/Dockerfile`, `docker-compose.yml`, `.dockerignore`.
- [ ] `docker compose up --build` runs the whole stack (3000 / 8000 / 8000/docs).

## Deliverable 6 — AI chat history
- [ ] `docs/ai-chat-history/` populated per phase (templates in place).
- [ ] All prompts recorded; no secrets included.

## README completion-status disclosure
- [ ] "What is done / partially done / pending" section present.
- [ ] Deadline conflict noted (PDF 29 Jul 2026 vs current date) with resolution.

## Final
- [ ] All acceptance criteria in `specs/10-acceptance-criteria.md` reviewed.
- [ ] Submit: live link, paper PDF, diagram URL, repo URL, Docker note, AI chat history.
