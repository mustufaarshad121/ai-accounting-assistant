# Workflow Diagram Content

Exact content to reproduce in **draw.io or Lucidchart** (tool choice is a hard requirement). Build
the diagram, then paste its **public shareable URL** into the README and commit a PNG/PDF export.

## Nodes (draw these as boxes)

| # | Node | Type / note |
|---|------|-------------|
| 1 | **User** | actor |
| 2 | **Next.js Frontend** | App Router pages + forms + assistant chat |
| 3 | **FastAPI API** | `/api/v1` routes |
| 4 | **Pydantic Validation** | request/response models (gate on every request) |
| 5 | **LangGraph Agent** | single accounting agent (state machine) |
| 6 | **Approved Agent Tools** | ~19 structured tools (no direct SQL) |
| 7 | **Accounting Services** | journal/entry service, balance logic |
| 8 | **Report Services** | trial balance, P&L, balance sheet, monthly review |
| 9 | **Supabase PostgreSQL** | accounts, journal_entries, journal_lines, chat_*, audit_* |
| 10 | **Response to User** | rendered result / confirmation |

Shared rule to annotate on the canvas: **Only Accounting Services and Report Services touch the
database. The LLM reaches data exclusively through Approved Agent Tools. Financial totals are
computed by deterministic services, never by the model.**

---

## Flow 1 — Manual accounting-entry flow
User → Next.js form → FastAPI (`POST /api/v1/entries/expense`) → Pydantic Validation →
Accounting Services (assert debits = credits, POSTED) → PostgreSQL → Response (entry number) →
Next.js ledger.

## Flow 2 — AI accounting-entry flow
User (chat: "Add office rent 50,000 for July") → Next.js → FastAPI (`POST /api/v1/assistant/chat`)
→ Pydantic → LangGraph Agent → (tool: `create_expense_entry`) Approved Tools → Accounting
Services → PostgreSQL → Response states operation, debit acct, credit acct, amount, date, entry
number → Next.js.

## Flow 3 — Missing-information clarification flow
User ("Add office rent 50,000") → LangGraph Agent detects missing fields (date? cash/bank? or
payable?) → **NO DB write** → Agent asks clarifying question → User answers → Agent proposes
preview → User confirms → then Flow 2 completes. Draw a decision diamond: *"Required info
present?"* No → ask; Yes → *"User confirmed?"* No → preview; Yes → write.

## Flow 4 — Report-generation flow
User → Next.js report page (date filters) → FastAPI (`GET /api/v1/reports/trial-balance` etc.) →
Pydantic → Report Services (deterministic SQL aggregation) → PostgreSQL → totals → Response →
Next.js renders. (Same path when triggered via agent tool `generate_*`.)

## Flow 5 — Monthly accounting-review flow
User → `GET /api/v1/reports/monthly-review?month=YYYY-MM` → Report Services run deterministic
checks (unbalanced, duplicates, missing descriptions/accounts, zero/negative, future dates,
abnormally large, revenue/expense misposting, post-posting edits, missing refs, reversal
inconsistencies) → findings with severity INFO/WARNING/CRITICAL → PostgreSQL (`audit_runs`,
`audit_findings`) → optional agent summary → Response.

## Flow 6 — Error and validation flow
Any request failing Pydantic validation or a business rule (e.g., unbalanced entry, invalid account,
future date, editing a POSTED entry) → FastAPI returns structured error (422 / 400 / 409) →
Next.js shows validation / API error state. Draw as a branch off nodes 4 and 7 returning a red
error path to node 10.

---

## Layout suggestion
- Left column: User, Next.js. Middle: FastAPI + Pydantic. Upper-middle branch: LangGraph → Tools.
  Right: Accounting Services + Report Services → PostgreSQL. Return arrows to "Response to User".
- Use one color per flow (legend in a corner) so all six flows are distinguishable on one canvas.
