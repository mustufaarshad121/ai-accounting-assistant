# 07 — Report Specifications

All reports are computed by **deterministic Python services** from PostgreSQL data. The LLM never
computes or invents totals. Only **POSTED** entries count toward balances (DRAFT excluded; REVERSED
entries and their reversals net to zero and are included so the books stay consistent). All money is
`Decimal`.

## Normal balance convention
- ASSET, EXPENSE: normal **debit** balance = Σdebit − Σcredit.
- LIABILITY, EQUITY, REVENUE: normal **credit** balance = Σcredit − Σdebit.

---

## 1. Trial Balance
- **Input:** `as_of` date (optional; default today).
- **Logic:** for each active account, sum debits and credits of POSTED lines with `entry_date <= as_of`.
  Net into a single debit or credit balance per account by normal balance.
- **Output:** rows `{account_code, account_name, account_type, debit_balance, credit_balance}` plus
  `total_debit`, `total_credit`, `balanced` (`total_debit == total_credit`).
- **Business rule:** totals must be equal; `balanced=false` indicates a data problem (should not
  happen if postings are enforced).
- **Edge:** no entries → all zeros, balanced=true. **Acceptance:** totals equal after any set of
  balanced postings.

## 2. Profit and Loss
- **Input:** `start`, `end` (inclusive).
- **Logic:** REVENUE grouped by account = Σcredit − Σdebit within range; EXPENSE grouped by account =
  Σdebit − Σcredit within range. `net_profit = total_revenue − total_expenses`.
- **Output:** `revenue[]`, `expenses[]` (per-account), `total_revenue`, `total_expenses`, `net_profit`
  (negative = net loss).
- **Edge:** empty range → zeros, net 0. **Acceptance:** P&L over a period equals sum of its
  per-account figures; matches manual calc on seeded data.

## 3. Balance Sheet
- **Input:** `as_of` date.
- **Logic:**
  - Assets = Σ asset-account balances (debit-normal) as of date.
  - Liabilities = Σ liability-account balances (credit-normal) as of date.
  - Equity = Owner Capital (3000) − Owner Drawings (3100) + **current-period earnings**
    (retained/earnings = cumulative REVENUE − EXPENSE up to `as_of`).
- **Output:** `assets[]`, `liabilities[]`, `equity{owner_capital, owner_drawings,
  current_period_earnings, total_equity}`, `total_assets`, `total_liabilities_and_equity`, `balanced`.
- **Validate:** `Assets == Liabilities + Equity`. Nothing hard-coded.
- **Edge:** only owner capital posted → Assets(Cash)=Capital, balanced. **Acceptance:** equation holds
  on all seeded scenarios.

## 4. Automated Monthly Accounting Review
(Named **Automated Monthly Accounting Review** — not a statutory/external audit.)
- **Input:** `start`, `end`.
- **Logic:** deterministic rules produce findings; the AI may only *summarize* them.
- **Rules → severity:**
  - Unbalanced entry → CRITICAL
  - Negative debit/credit → CRITICAL
  - Missing account on a line → CRITICAL
  - Reversal inconsistency (reversal not balancing original / bad reference) → CRITICAL
  - Entry changed after posting (`updated_at > created_at` while POSTED) → WARNING
  - Duplicate transaction (same date+amount+description) → WARNING
  - Future-dated transaction (`entry_date > today`) → WARNING
  - Abnormally large transaction (> threshold, e.g. configurable) → WARNING
  - Revenue posted to expense account / expense to revenue account → WARNING
  - Missing reference where expected → INFO
  - Missing description → INFO
  - Zero-value transaction → INFO
- **Output:** `findings[{rule_code, severity, message, entry_id?, details?}]`,
  `counts_by_severity`, optional AI `summary`. Persisted to `audit_runs` / `audit_findings`.
- **Acceptance:** each rule has a test that seeds a triggering row and asserts the finding + severity.
