# 00 — Assignment Requirements (Source of Truth)

This file records the **mandatory** requirements as extracted verbatim-in-substance
from `docs/intern-assignment.pdf` (4 pages, read in full). Nothing here is invented;
where the approved MVP prompt adds detail, it is marked as a **refinement**, not a PDF requirement.

## Project
- Full-stack web app + integrated **AI service** that automates an accountant / CA's day-to-day work.
- User (office admin / business owner) manages financial records: daily expenses, monthly office
  expenses, income entries — via a modern web UI, with an AI agent automating tasks.
- "The AI service is the heart of this project." Natural-language operations: add/update entries,
  generate P&L, prepare balance sheet, run an audit for a month, summarize spending,
  answer questions like "How much did we spend on utilities in March?".
- The PDF **intentionally does not give a fixed feature list** — discovering CA tasks and their AI
  automation is part of the graded research.

## Phase 1 — Research & Research Paper (PDF)
Must cover (minimum): accountant/CA responsibilities and daily/monthly/yearly tasks (bookkeeping,
ledgers, journal entries, expense tracking, balance sheet, P&L, trial balance, cash flow, audits,
tax summaries, reconciliation); which tasks are AI-automatable and how; how agentic frameworks work
+ comparison of **at least 2–3** options with justification; AI model choice + why (cost, capability,
free-tier); proposed system architecture; **exact feature list**; references.
Recommended length **6–15 pages**. Must be own writing, defensible in review.

## Phase 2 — Spec-Driven Development
- Write clear specs first, implement against them. Specs define features, API contracts, data models,
  AI-agent behavior. Keep in a **/specs** folder.
- **Workflow diagram on Lucidchart or draw.io (mandatory tool)** covering user flows, AI agent flow
  (UI → API → agent → tools → database → response), data flow. **Shareable URL must be submitted**;
  keep a PNG/PDF export in repo.

## Phase 3 — Development
- **UI (Next.js + TypeScript):** screens for daily expenses, monthly office expenses, income,
  ledgers/records list, reports (P&L, balance sheet, audit view), and an AI chat/assistant interface.
- **Manual + AI-driven entry:** forms and natural language ("Add office rent 50,000 for July").
- **AI automation:** create/read/update entries, generate P&L, prepare balance sheet, run a monthly
  audit, answer any accounts question from the data.
- **Reports:** generated from real PostgreSQL data (**not hard-coded**).
- **Validation:** all API request/response models use **Pydantic**.

## Phase 4 — Deployment
- Deploy frontend + backend + database on **free** hosting (Vercel; Railway/Render/HF Spaces/Fly.io;
  Neon/Supabase/Railway). Live link must work at submission.
- Complete **Docker setup** (Dockerfile(s) + docker-compose) so the project runs locally with Docker.

## Section 3 — Required Tech Stack (verbatim substance)
| Layer | Requirement |
|---|---|
| Frontend | Next.js with TypeScript |
| Backend | Python, managed with **uv** |
| API Framework | FastAPI |
| Data Validation | Pydantic models (all request/response schemas) |
| Database | PostgreSQL |
| AI Model | Developer's choice — any model (free-tier friendly fine) |
| Agentic Framework | Any code-based framework (OpenAI Agents SDK, LangGraph, CrewAI, etc.) — justified |
| Methodology | Spec-Driven Development |
| Workflow Diagram Tool | Lucidchart or draw.io (mandatory); shareable URL submitted |
| Containerization | Docker (Dockerfile + docker-compose) |

## Section 4 — GitHub & Version Control
- Public / shared-access GitHub repo; submit URL.
- **Every feature on its own branch** (e.g. `feature/expense-entry`, `feature/ai-agent`,
  `feature/pl-report`) merged into `main` via **pull requests**.
- Commits **frequent, small, meaningful** (e.g. `feat: add monthly audit endpoint`,
  `fix: expense date validation`). A single giant "final commit" is **heavily penalized**.
- Repo must include: clear README (setup + run), `/specs`, workflow diagram (image/PDF or link),
  Docker setup.

## Section 5 — Deliverables
1. Live deployment link (frontend ↔ backend ↔ database).
2. Research paper (PDF).
3. Workflow diagram URL (Lucidchart/draw.io) + repo export.
4. GitHub repo URL (branches, commits, README, specs).
5. Docker setup (one-command run).
6. **AI chat history** — every AI tool used (Claude, Gemini CLI, Codex, etc.), all prompts.

## Section 6 — Deadline & Submission Policy
- **Deadline: Wednesday, 29 July 2026.** No extensions. Partial-but-on-time is acceptable;
  late is not. Include a note stating what is done / partial / pending.

> **DEADLINE NOTE (do not alter the source date above):**
> The assignment PDF contains the original deadline of 29 July 2026. The candidate reports
> receiving a separate updated deadline. The updated deadline must be verified from the
> employer's written communication.
>
> The updated deadline has **not** been verified — no written evidence exists in this
> repository at this time. Do not treat any revised date as confirmed until such written
> evidence is added here. All planning proceeds as an urgent MVP regardless.

## Section 7 — Suggested Order (guidance, not binding)
Days 1–2 research + paper + feature list; Day 2 diagram + specs + schema; Days 3–4 repo, Docker,
PostgreSQL, FastAPI + Pydantic + core CRUD, start Next.js; Day 4–5 AI agent + reports; Day 5 deploy,
test, README, submit. **Tip:** thin end-to-end slice first (one AI-created expense → PostgreSQL → UI),
then expand feature-by-feature on branches.

## Non-negotiable rules
- Plagiarism rejected. Must explain every part in review. No hard-coded financial totals.
- Pydantic for all request/response models. Free hosting only.
