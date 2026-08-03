# 08 — Security and Validation

## Purpose
Define validation layers, financial-integrity guarantees, and security posture for the MVP.
Authentication is **out of scope now** (see `01-project-scope.md`); this spec prepares for it without
implementing it.

## Validation layers
1. **Pydantic (edge):** every request/response and every agent tool argument is a Pydantic model.
   Amounts are positive `Decimal`; dates are valid ISO dates; enums constrained (account type,
   status, source).
2. **Service (invariants):** double-entry balance enforced (Σdebit == Σcredit); each line has exactly
   one of debit/credit > 0; referenced accounts exist and are active and of the correct type for the
   template; transfer from ≠ to.
3. **Database (constraints):** `NUMERIC(precision, 2)` for money (never float); FKs on
   `account_id`, `journal_entry_id`, `reversed_entry_id`; check constraints (debit ≥ 0, credit ≥ 0);
   unique `entry_number`; enum-backed status/source/type.

## Financial integrity
- Money is `Decimal`/`NUMERIC` end-to-end; serialized as strings in JSON.
- Posting is atomic (single transaction); an unbalanced entry is rejected before commit.
- POSTED entries are immutable: no hard delete, correction only via reversal + replacement with
  preserved references (`reversed_entry_id`).
- Reports read only POSTED entries; LLM cannot alter or invent figures.

## AI safety
- Agent uses approved tools only; **no direct SQL**, no filesystem, no network beyond the model API.
- Mandatory clarification for missing accounting data; mandatory preview/confirmation before write,
  update, or reversal (see `06`).
- All tool calls logged (`agent_tool_calls`) with args, result, status for auditability.
- Model output treated as untrusted: it selects tools and phrases responses but figures come from
  services.

## Secrets & config
- All secrets via environment variables; `.env.example` holds placeholders only; real `.env` is
  git-ignored. Never log or echo secret values. Keys referenced by name only.

## Transport / CORS
- Backend CORS restricted to `FRONTEND_URL`. HTTPS in production (platform-provided).
- `SUPABASE_SECRET_KEY` used server-side only; never shipped to the browser. Only
  `NEXT_PUBLIC_*` vars reach the client.

## Prepared-for-later (not implemented now)
- `profiles` table + `user_id` columns can be added when Supabase Auth is introduced; FastAPI would
  then validate the Supabase access token. Only email/password auth + protected routes are in scope
  for that later phase — no social/phone/MFA/roles.

## Acceptance
- Unbalanced entry → HTTP 400/422, nothing committed.
- Negative/zero amount, invalid date, unknown/inactive account → 422/400 with clear message.
- PATCH on POSTED entry → 409. Reverse on non-POSTED → 409.
- No secret value appears in logs, responses, or committed files.
