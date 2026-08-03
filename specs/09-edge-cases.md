# 09 — Edge Cases

Consolidated edge-case catalogue across accounting, API, reports, and AI. Each is either enforced by a
validation layer (`08`) or handled by a service, and should map to a test (`docs/testing-plan.md`).

## Journal entries / posting
- **Unbalanced entry** (Σdebit ≠ Σcredit) → reject (422/400), nothing committed.
- **Line with both debit and credit > 0**, or both zero → reject.
- **Negative debit or credit** → reject.
- **Zero-total entry** (all lines zero) → reject.
- **Single-line entry** → reject (needs ≥ 2 lines to balance).
- **Unknown / inactive account referenced** → reject.
- **Wrong account type for template** (e.g. income credited to an EXPENSE account) → reject at service
  level for typed endpoints; flagged by review for generic entries.
- **Duplicate entry_number** → DB unique constraint; service generates numbers to avoid collision.
- **Very large amount** → allowed (posts), but flagged WARNING by monthly review.
- **Future-dated entry** → allowed (posts), but flagged WARNING by review.

## Updates / reversals
- **PATCH a POSTED entry** → 409; must reverse + replace instead.
- **PATCH a DRAFT** → allowed.
- **Reverse a non-POSTED entry** (DRAFT/REVERSED) → 409.
- **Reverse an already-reversed entry** → 409 (idempotency; check `reversed_entry_id` chain).
- **Reversal must mirror original** (swap debits/credits, equal totals) → enforced.

## Transfers
- **Transfer from == to account** → reject.
- **Transfer involving non-cash/bank account** → reject (template restricted to ASSET cash/bank).

## Reports
- **Empty database** → all reports return zeros, `balanced=true`, no error.
- **P&L start > end** → 422.
- **Balance sheet before any postings** → zeros, balanced.
- **as_of / range excludes all entries** → zeros.
- **DRAFT entries** → never included in report figures.

## AI agent
- **Missing accounting info** (date, cash vs bank, payable vs paid) → agent asks, does **not** write.
- **User declines confirmation** → no write; entry not created.
- **Ambiguous account** ("supplies" vs "office supplies") → agent lists candidates / asks.
- **Model proposes unbalanced entry** → tool/service rejects; agent must correct, never force.
- **Model invents a total** → prevented: figures come only from deterministic services.
- **Amount only, no currency/scale** → agent confirms amount as given (single-currency MVP).

## Data / precision
- **Float money** → forbidden; `Decimal`/`NUMERIC(…,2)` everywhere.
- **Rounding** → half-up to 2 decimals at service boundary; balance check uses exact Decimal.

## Infra
- **DB unreachable** → 503 on `/health` dependency check and on data routes; clear error surfaced in UI.
- **LLM endpoint unreachable / rate-limited** → agent returns graceful error; no partial write.
- **CORS from unlisted origin** → blocked.
