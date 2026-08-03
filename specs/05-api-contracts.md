# 05 — API Contracts

All routes under `/api/v1` (except `/health`). Every request/response uses **Pydantic** models.
Routes are thin; business logic lives in services. Money serialized as decimal strings.

## Conventions
- Errors: `{ "detail": <string | structured> }` with HTTP 400/404/409/422.
- Dates: ISO `YYYY-MM-DD`. Amounts: positive decimals as strings (e.g. `"50000.00"`).
- List endpoints support pagination (`limit`, `offset`) and filters where noted.

## Health
`GET /health` → `{ "status": "ok" }`.

## Accounts
- `GET /api/v1/accounts?type=&is_active=` → `[AccountOut]`.
- `POST /api/v1/accounts` body `AccountCreate{code,name,type}` → `AccountOut` (201).

`AccountOut{ id, code, name, type, is_active, created_at }`.

## Entries — read/list
- `GET /api/v1/entries?start=&end=&account_id=&source=&status=&q=&limit=&offset=`
  → `EntryListOut{ items:[EntryOut], total }`. Supports search (`q` over description/reference) and
  date/account/source/status filters. This backs ledger, income, daily/monthly expense views.
- `GET /api/v1/entries/{entry_id}` → `EntryOut` (404 if missing).

`EntryOut{ id, entry_number, entry_date, description, source, status, reference,
reversed_entry_id, lines:[LineOut], total_debit, total_credit, created_at, updated_at }`.
`LineOut{ id, account_id, account_code, account_name, debit, credit, memo }`.

## Entries — create (one route per template)
Each returns `EntryOut` (201) and posts a balanced entry.
- `POST /api/v1/entries/income` — `IncomeCreate{ amount, date, description, deposit_account_id(Cash/Bank), revenue_account_id, memo? }`.
- `POST /api/v1/entries/expense` — `ExpenseCreate{ amount, date, description, expense_account_id, paid_from_account_id(Cash/Bank), memo? }`.
- `POST /api/v1/entries/owner-capital` — `OwnerCapitalCreate{ amount, date, description, deposit_account_id, memo? }`.
- `POST /api/v1/entries/vendor-bill` — `VendorBillCreate{ amount, date, description, expense_or_asset_account_id, memo? }` (Cr Accounts Payable).
- `POST /api/v1/entries/vendor-payment` — `VendorPaymentCreate{ amount, date, description, paid_from_account_id, memo? }` (Dr Accounts Payable).
- `POST /api/v1/entries/owner-withdrawal` — `OwnerWithdrawalCreate{ amount, date, description, paid_from_account_id, memo? }`.
- `POST /api/v1/entries/transfer` — `TransferCreate{ amount, date, description, from_account_id, to_account_id, memo? }` (from ≠ to).

Validation: amount > 0; accounts exist/active; correct account types per template; balance enforced.

## Entries — update / reverse
- `PATCH /api/v1/entries/{entry_id}` — `EntryUpdate{ description?, entry_date?, reference?, lines? }`.
  Allowed only when `status=DRAFT`; POSTED → 409 (use reverse).
- `POST /api/v1/entries/{entry_id}/reverse` — body `ReverseRequest{ reason? }` →
  `EntryOut` of the reversal entry. POSTED only; already-REVERSED/DRAFT → 409.

## Reports (read-only, deterministic)
- `GET /api/v1/reports/trial-balance?as_of=` → `TrialBalanceOut{ as_of, rows:[{account_code,
  account_name, account_type, debit_balance, credit_balance}], total_debit, total_credit, balanced }`.
- `GET /api/v1/reports/profit-loss?start=&end=` → `ProfitLossOut{ start, end,
  revenue:[{account_code,account_name,amount}], expenses:[...], total_revenue, total_expenses,
  net_profit }`.
- `GET /api/v1/reports/balance-sheet?as_of=` → `BalanceSheetOut{ as_of, assets:[...],
  liabilities:[...], equity:{owner_capital, owner_drawings, current_period_earnings, total_equity},
  total_assets, total_liabilities_and_equity, balanced }`.
- `GET /api/v1/reports/monthly-review?start=&end=` → `MonthlyReviewOut{ period_start, period_end,
  findings:[{rule_code, severity, message, entry_id?, details?}], counts_by_severity, summary? }`.

## Assistant (AI)
- `POST /api/v1/assistant/chat` — `ChatRequest{ thread_id?, message }` → `ChatResponse{ thread_id,
  messages:[{role,content}], pending_action? , created_entry? }`. The agent may return a preview
  requiring confirmation (`pending_action`); a follow-up message confirms.
- `GET /api/v1/assistant/threads/{thread_id}` → `ThreadOut{ id, title, messages:[ChatMessageOut] }`.

## Business-logic placement
No accounting math in route functions. Routes call `AccountingService`, `ReportService`,
`ReviewService`, and the agent. Agent tools call the same services.

## Acceptance
Every route above exists, is typed with Pydantic in and out, returns documented status codes, and is
visible in `/docs` (OpenAPI).
