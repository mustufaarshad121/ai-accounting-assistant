# 03 — Database Schema

## Purpose
Define the PostgreSQL schema for double-entry accounting, chat, and the monthly review. Money is
`NUMERIC(18,2)` — never floating point. Timestamps are `timestamptz`. IDs are UUID.

## Design rule
There are **no** `daily_expenses`, `monthly_expenses`, or `income` source tables. Those views are
**derived** from `accounts` + `journal_entries` + `journal_lines` + date filters.

## Tables

### profiles (prepared for future auth; may stay unused)
| column | type | notes |
|---|---|---|
| id | uuid PK | matches Supabase auth user id when auth added |
| email | text | nullable until auth |
| full_name | text | nullable |
| created_at | timestamptz | default now() |

### accounts
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| code | varchar(10) UNIQUE NOT NULL | e.g. "5100" |
| name | text NOT NULL | e.g. "Utilities" |
| type | enum account_type NOT NULL | ASSET/LIABILITY/EQUITY/REVENUE/EXPENSE |
| is_active | boolean NOT NULL default true | |
| created_at | timestamptz default now() | |

`account_type` enum: `ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE`.
Normal balance: ASSET & EXPENSE = debit; LIABILITY, EQUITY, REVENUE = credit.

### journal_entries
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| entry_number | varchar UNIQUE NOT NULL | e.g. "JE-2026-000123" |
| entry_date | date NOT NULL | transaction date |
| description | text NOT NULL | required (review flags missing) |
| source | enum entry_source NOT NULL | MANUAL/AI/SYSTEM/IMPORT |
| status | enum entry_status NOT NULL | DRAFT/POSTED/REVERSED |
| reference | text NULL | external ref / correction link |
| reversed_entry_id | uuid NULL FK→journal_entries.id | set on a reversal entry pointing to original |
| created_at | timestamptz default now() | |
| updated_at | timestamptz default now() | |

`entry_status` enum: `DRAFT, POSTED, REVERSED`.
`entry_source` enum: `MANUAL, AI, SYSTEM, IMPORT`.

### journal_lines
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| journal_entry_id | uuid FK→journal_entries.id NOT NULL | ON DELETE handled via reversal, not cascade delete of posted |
| account_id | uuid FK→accounts.id NOT NULL | |
| debit | numeric(18,2) NOT NULL default 0 | ≥ 0 |
| credit | numeric(18,2) NOT NULL default 0 | ≥ 0 |
| memo | text NULL | |

Line rule: exactly one of debit/credit > 0 (the other = 0); both may not be 0; neither negative.

### chat_threads
| id uuid PK | title text | created_at timestamptz | updated_at timestamptz |

### chat_messages
| id uuid PK | thread_id uuid FK→chat_threads | role enum(user/assistant/tool/system) | content text | created_at timestamptz |

### agent_tool_calls
| id uuid PK | message_id uuid FK→chat_messages NULL | thread_id uuid FK→chat_threads | tool_name text | arguments jsonb | result jsonb | status text(success/error) | created_at timestamptz |

### audit_runs (Automated Monthly Accounting Review runs)
| id uuid PK | period_start date | period_end date | run_at timestamptz | summary text NULL | created_at timestamptz |

### audit_findings
| id uuid PK | audit_run_id uuid FK→audit_runs | rule_code text | severity enum(INFO/WARNING/CRITICAL) | message text | journal_entry_id uuid FK→journal_entries NULL | details jsonb NULL | created_at timestamptz |

## Constraints & invariants
- Sum(debit) = Sum(credit) per POSTED entry (enforced in service; a CHECK cannot span rows, so
  balance is validated in the accounting service inside a transaction).
- `debit >= 0` and `credit >= 0` (CHECK).
- `entry_number` unique. `code` unique.
- Posted entries never deleted; corrections via reversal (`reversed_entry_id`).

## Migrations
Alembic, applied in **phases** that match the feature branches. Each phase adds only the tables its
feature needs, so a branch never ships schema for capabilities it hasn't built. All tables above
remain part of the final architecture; they are introduced in this order:

| Phase / branch | Alembic revision adds | Tables |
|---|---|---|
| `feature/accounting-core` | accounting enums + core ledger | `accounts`, `journal_entries`, `journal_lines` |
| `feature/reports` | monthly-review persistence | `audit_runs`, `audit_findings` |
| `feature/ai-agent` | assistant persistence | `chat_threads`, `chat_messages`, `agent_tool_calls` |
| later auth phase | prepared-for-auth (see `08`) | `profiles` |

The **accounting-core** revision creates the three accounting enums (`account_type`, `entry_source`,
`entry_status`) plus `accounts`, `journal_entries`, and `journal_lines` — with foreign keys, indexes,
the unique `entry_number`/`code` constraints, and the per-line monetary CHECK constraints. It must
**not** create the chat, audit, or `profiles` tables; those arrive in their own later revisions. The
default chart of accounts (see `04-accounting-rules.md`) is inserted by an **idempotent seed process**
(re-runnable without creating duplicates), kept separate from the schema migration.

## Edge cases
- Concurrent entry-number generation → generate inside a transaction / sequence per year.
- Reversal of an already-reversed entry → rejected (see accounting rules).
- Deleting a POSTED entry → rejected at service layer.

## Acceptance
The accounting-core Alembic upgrade creates the three accounting enums + `accounts`,
`journal_entries`, `journal_lines` (and its downgrade reverses them cleanly); the idempotent seed
inserts the 18 default accounts without duplicating on re-run; a balanced entry with 2 lines
persists; an unbalanced entry is rejected before commit. Later phases add the audit, chat, and
`profiles` tables in their own revisions.
