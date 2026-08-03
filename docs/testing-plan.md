# Testing Plan

Backend tests use pytest against a test PostgreSQL (or transactional rollbacks). Agent tests use
**mocked model responses** to avoid API cost. Frontend checks use component/integration tests.

## Backend — accounting core
- [ ] Balanced journal entry posts successfully.
- [ ] Unbalanced entry is rejected (422/400), nothing committed.
- [ ] Line with both debit and credit > 0 rejected; both-zero line rejected.
- [ ] Negative debit or credit rejected.
- [ ] Zero-amount / zero-total entry rejected.
- [ ] Income posting: correct Dr Cash/Bank, Cr Revenue; balanced.
- [ ] Expense posting: correct Dr Expense, Cr Cash/Bank; balanced.
- [ ] Owner capital posting: Dr Cash/Bank, Cr Owner Capital.
- [ ] Vendor bill: Dr Expense/Asset, Cr Accounts Payable.
- [ ] Vendor payment: Dr Accounts Payable, Cr Cash/Bank.
- [ ] Owner withdrawal: Dr Owner Drawings, Cr Cash/Bank.
- [ ] Transfer: Dr destination, Cr source; from==to rejected.
- [ ] Reversal: swaps sides, links `reversed_entry_id`, sets original REVERSED.
- [ ] Reverse a DRAFT / already-REVERSED entry → 409.
- [ ] PATCH POSTED entry → 409; PATCH DRAFT allowed.
- [ ] Posted entry cannot be hard-deleted.
- [ ] Unique entry_number generation under repeated posts.

## Backend — reports
- [ ] Trial Balance: total_debit == total_credit on seeded data.
- [ ] P&L: net_profit == total_revenue − total_expenses; groups sum to totals; start>end → 422.
- [ ] Balance Sheet: Assets == Liabilities + Equity; equity = capital − drawings + current earnings.
- [ ] Empty DB: all reports zeros, balanced, no error.
- [ ] DRAFT entries excluded from all report figures.

## Backend — monthly review (one test per rule)
- [ ] Unbalanced → CRITICAL; negative amount → CRITICAL; missing account → CRITICAL;
      reversal inconsistency → CRITICAL.
- [ ] Changed-after-posting → WARNING; duplicate → WARNING; future-dated → WARNING;
      abnormally large → WARNING; revenue↔expense misposting → WARNING.
- [ ] Missing reference → INFO; missing description → INFO; zero-value → INFO.
- [ ] `counts_by_severity` matches emitted findings.

## Backend — validation
- [ ] Pydantic rejects invalid amount type, missing required fields.
- [ ] Invalid date string → 422. Future date allowed at post, flagged by review.
- [ ] Invalid / inactive account id → 400/404.
- [ ] Zero and negative amounts → 422.

## Backend — AI agent (mocked model)
- [ ] Mocked tool-call flow creates an income entry (source=AI).
- [ ] "Add office rent 50,000" → agent asks for date + cash/bank/payable; no write yet.
- [ ] Preview returned before post; write only after confirmation.
- [ ] Successful write response states operation, debit acct, credit acct, amount, date, entry number.
- [ ] Spending question returns service-sourced figure (no model arithmetic).
- [ ] Tool call logged to `agent_tool_calls`.

## Frontend checks
- [ ] Successful API loading renders data.
- [ ] API error response → error state shown.
- [ ] Empty dataset → empty state shown.
- [ ] Form validation blocks bad input with messages.
- [ ] Report pages render figures from API (no hard-coded totals).
- [ ] Chat response renders assistant messages + preview/confirmation.

## Tooling
- Backend: `uv run pytest`. Frontend: `npm test` (or `vitest`/RTL) + `npm run lint`.
- CI (optional): run backend + frontend tests on PRs.
