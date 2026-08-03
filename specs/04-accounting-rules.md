# 04 — Accounting Rules

## Purpose
Define the double-entry rules, default chart of accounts, transaction templates, and posting/reversal
logic. These rules are authoritative for the accounting service.

## Double-entry fundamentals
- Every entry has ≥ 2 lines. **Total debits = total credits.** Unbalanced → rejected.
- Normal balances: **ASSET, EXPENSE → debit**; **LIABILITY, EQUITY, REVENUE → credit**.
- Each line: one side positive, other zero; no negatives; not both zero.
- Amounts are `Decimal` / `NUMERIC(18,2)`.

## Default chart of accounts (seed)
| code | name | type |
|---|---|---|
| 1000 | Cash | ASSET |
| 1010 | Bank | ASSET |
| 1100 | Accounts Receivable | ASSET |
| 1200 | Prepaid Expenses | ASSET |
| 1500 | Equipment | ASSET |
| 2000 | Accounts Payable | LIABILITY |
| 2100 | Loan Payable | LIABILITY |
| 3000 | Owner Capital | EQUITY |
| 3100 | Owner Drawings | EQUITY |
| 4000 | Sales Revenue | REVENUE |
| 4100 | Service Revenue | REVENUE |
| 5000 | Office Rent | EXPENSE |
| 5100 | Utilities | EXPENSE |
| 5200 | Office Supplies | EXPENSE |
| 5300 | Salaries | EXPENSE |
| 5400 | Marketing Expense | EXPENSE |
| 5500 | Travel Expense | EXPENSE |
| 5600 | Miscellaneous Expense | EXPENSE |

## Transaction templates (debit → credit)
1. **Owner investment** — Dr Cash/Bank · Cr Owner Capital (3000).
2. **Cash income** — Dr Cash/Bank · Cr Revenue (4000/4100).
3. **Cash expense** — Dr Expense (5xxx) · Cr Cash/Bank.
4. **Vendor bill** — Dr Expense/Asset · Cr Accounts Payable (2000).
5. **Vendor payment** — Dr Accounts Payable (2000) · Cr Cash/Bank.
6. **Owner withdrawal** — Dr Owner Drawings (3100) · Cr Cash/Bank.
7. **Fund transfer** — Dr destination Cash/Bank · Cr source Cash/Bank.

Each template takes: amount (>0), date, description, relevant account selections. Service builds the
two lines from the template, enforces balance, assigns entry number, posts.

## Entry numbering
`JE-{YYYY}-{zero-padded sequence}` per calendar year, generated inside the posting transaction to
avoid duplicates.

## Posting rules
- New transactions post as `status=POSTED` unless explicitly created as `DRAFT`.
- `source` = MANUAL (API forms), AI (agent), SYSTEM (seed/automation), IMPORT (future).

## Update rules
- **DRAFT**: lines/description/date editable; may be deleted.
- **POSTED**: immutable financially. To correct → reverse + create corrected entry.
- **REVERSED**: terminal; not editable.

## Reversal rules
- Reversing a POSTED entry creates a new entry with swapped debit/credit lines, `source=SYSTEM`
  (or same as trigger), `reversed_entry_id` = original id, and sets the original to `REVERSED`.
- Cannot reverse a DRAFT (nothing posted) or an already-REVERSED entry.
- Correction chain preserved: original → reversal (`reversed_entry_id`) → replacement (`reference`).

## Validation / Errors
- Unbalanced → 422 "debits must equal credits".
- Nonexistent/inactive account → 404/400.
- Amount ≤ 0 → 422. Future date → allowed but flagged by monthly review (WARNING).
- Delete POSTED → 409 "posted entries cannot be deleted; use reversal".

## Edge cases
- Same source & destination in transfer → reject.
- Expense template pointed at a REVENUE account → reject at service (type mismatch); monthly review
  also flags misposting historically.
- Rounding: all math in Decimal, quantize to 2 places.

## Acceptance
Each of the 7 templates produces a balanced POSTED entry; unbalanced rejected; reversal swaps sides
and links ids; posted delete blocked.
