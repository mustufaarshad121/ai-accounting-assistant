# 06 — AI Agent Behavior

## Purpose
Define the single LangGraph accounting agent: its tools, clarification/confirmation rules, and
response contract. The agent **never** computes financial totals itself and **never** runs SQL — it
only calls approved tools that delegate to the same deterministic services the API uses.

## Framework
One **LangGraph** agent (not multi-agent). OpenAI-compatible model via `LLM_API_KEY`,
`LLM_BASE_URL`, `LLM_MODEL`. Tool arguments are structured **Pydantic** models.

## Approved tools (only these)
Write/mutate: `create_owner_capital_entry`, `create_income_entry`, `create_expense_entry`,
`create_vendor_bill`, `record_vendor_payment`, `create_owner_withdrawal`, `transfer_funds`,
`update_draft_entry`, `reverse_posted_entry`.
Read/report: `get_entry`, `search_entries`, `list_accounts`, `get_account_balance`,
`generate_trial_balance`, `generate_profit_and_loss`, `generate_balance_sheet`,
`summarize_spending`, `run_monthly_accounting_review`, `answer_financial_question`.

Each tool's arguments mirror the corresponding service/API contract in `05-api-contracts.md`.

## Clarification rule (must-ask before writing)
The agent must not assume accounting-relevant missing info. For "Add office rent of 50,000" it must
ask, at minimum:
- Transaction **date**.
- **Paid from cash or bank**, or **record as payable** (vendor bill)?
- Which expense account if ambiguous (default Office Rent 5000 if clearly rent, else confirm).
No DB write until required data is present.

## Confirmation rule (preview before mutation)
Before **posting a new transaction, updating a financial record, or reversing a posted entry**, the
agent returns a **preview** (accounts, debit/credit, amount, date) and waits for explicit user
confirmation. Only on confirmation does it call the write tool.

## Response contract (after a successful write)
The agent's message must clearly state:
- What operation was performed.
- Which account(s) **debited**.
- Which account(s) **credited**.
- The **amount**.
- The **date**.
- The resulting **entry number**.

## Read/question behavior
- Spending questions ("How much did we spend on utilities in March?") → `summarize_spending` /
  `answer_financial_question`, which query services; the agent reports the number the service
  returned, never an invented one.
- Report requests → call the matching report tool and present the returned figures verbatim.

## Safety
- Tool failure / validation error → agent surfaces the error and does not retry blindly; no partial
  writes (service posts atomically).
- Agent has no direct SQL, no filesystem, no ability to fabricate entry numbers.
- All tool calls logged to `agent_tool_calls` (name, args, result, status).

## Inputs / Outputs / Validation / Errors / Edge / Acceptance
- Inputs: chat message + thread history. Outputs: assistant messages + optional preview/created entry.
- Validation: Pydantic tool args + service invariants.
- Errors: returned as assistant messages describing the problem.
- Edge: ambiguous account, missing date, unbalanced (impossible via templates), reversal of
  non-posted → agent asks or explains.
- Acceptance: given "Add office rent 50,000" the agent asks for date + payment source before writing;
  after confirmation it posts a balanced entry and reports debits, credits, amount, date, entry number.
