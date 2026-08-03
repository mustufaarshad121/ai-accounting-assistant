# Research Paper Outline

Target: 6–15 pages, original writing, defensible in the review meeting. This is a **structured
outline with talking points** — not the final prose. The author must write and understand every
section. Where a claim requires a current market fact (pricing, model context windows, framework
release state), it is marked **[SOURCE REQUIRED]** and listed in the Research Checklist at the end — do
**not** fabricate these. `[SOURCE REQUIRED]` is the canonical marker used throughout this repository.

> Honesty rule: do not invent references or statistics. Cite only sources actually read.

---

## Title Page
- Title: *AI-Powered Accounting & Finance Assistant: Automating Double-Entry Bookkeeping with an Agentic LLM*
- Author, role (Full-Stack AI Developer Intern), date, repository URL.

## Abstract (½ page)
- Problem: manual bookkeeping is slow and error-prone for small offices.
- Solution: web app + single LangGraph agent that records entries and generates statements from
  real PostgreSQL data using deterministic services.
- Key stance: LLM never computes financial totals; it orchestrates approved tools only.

## 1. Introduction
- Motivation, target user (office admin / business owner), scope boundary (MVP, no tax filing).

## 2. Accountant / Chartered Accountant Responsibilities  *(topic 1)*
- Role of bookkeeper vs accountant vs CA; assurance/attest boundary.

## 3. Accounting Activity Cadence  *(topics 2–4)*
- **Daily:** record transactions, categorize expenses, capture income.
- **Monthly:** reconciliations, trial balance, management P&L, review/close.
- **Yearly:** adjusting entries, financial statements, tax prep support, audit support.

## 4. Bookkeeping Foundations  *(topics 5–11)*
- Bookkeeping & the accounting equation (Assets = Liabilities + Equity).
- Chart of accounts (5 types) → map to our 18 seeded accounts.
- Journal entries & double-entry (debits = credits).
- General ledger; Trial Balance; P&L; Balance Sheet — definitions + how each is derived here.

## 5. Cash, Receivables, Payables  *(topics 12–14)*
- Cash flow basics; AR (money owed to us); AP (money we owe). Note: cash-flow statement is
  **future scope** in the app — explain conceptually.

## 6. Reconciliation & Expense Categorization  *(topics 15–16)*
- What reconciliation verifies; why categorization drives reporting quality.

## 7. Audit & Anomaly Checks  *(topic 17)*
- Distinguish statutory audit from our "Automated Monthly Accounting Review".
- Enumerate the deterministic checks (unbalanced, duplicates, future dates, etc.).

## 8. Tax-Summary Limitations  *(topic 18)*
- Why the app does **not** file taxes or give tax advice; jurisdiction dependence.

## 9. What AI Can Automate vs Human Judgment  *(topics 19–20)*
- Automatable: NL entry creation, report generation, anomaly detection, categorization, Q&A.
- Human-required: judgment estimates, materiality, assurance opinions, regulatory sign-off.

## 10. Agentic Framework Comparison  *(topics 21–22)*
- Compare **LangGraph vs CrewAI vs OpenAI Agents SDK** across: control over graph/state,
  tool-calling model, human-in-the-loop / interrupts, provider lock-in, maturity. **[SOURCE REQUIRED]** current
  feature/release specifics.
- Justify LangGraph: explicit state machine, first-class interrupts for the confirm-before-post
  requirement, provider-agnostic via OpenAI-compatible endpoint.

## 11. AI Model Selection Criteria  *(topic 23)*
- Criteria: tool-calling reliability, cost, free-tier availability, context window, latency.
- Note config via `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`; specific model chosen is **[SOURCE REQUIRED]**.

## 12. System Architecture  *(topic 24)*
- Next.js → FastAPI → Pydantic → (services | LangGraph agent → tools → services) → PostgreSQL.
- Reference the workflow diagram; emphasize deterministic-services boundary.

## 13. Implemented Feature Scope  *(topic 25)*
- List exactly what the MVP ships (derived from specs). Keep honest vs pending.

## 14. Future Improvements  *(topic 26)*
- OCR, bank feeds/reconciliation, payroll, multi-currency, cash-flow statement, auth/RBAC, forecasting.

## 15. Security, Privacy, Hallucination & Financial-Risk Controls  *(topic 27)*
- No direct SQL for the model; tools only; confirm-before-write; deterministic totals; audit trail
  via reversal-not-delete; secrets via env; input validation with Pydantic.

## 16. Conclusion

## 17. References  *(topic 28)*
- Only sources actually consulted. Suggested types: official framework docs, accounting
  standards/education sources, FastAPI/SQLAlchemy docs. **Fill with real citations.**

---

## Research Checklist — [SOURCE REQUIRED] items to resolve before finalizing (do NOT fabricate)
- [ ] Current LangGraph / CrewAI / OpenAI Agents SDK feature & maturity comparison.
- [ ] Chosen LLM model name, context window, pricing, free-tier terms.
- [ ] Any statistic on bookkeeping error rates / time cost (cite source or drop).
- [ ] Exact versions of key libraries used (for reproducibility).
- [ ] Confirm accounting definitions against a citable standard/textbook.
