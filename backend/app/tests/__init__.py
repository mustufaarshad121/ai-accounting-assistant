"""Test package for the accounting core.

IMPORTANT — database coverage caveat
------------------------------------
The service tests run against an **in-memory SQLite** engine (``conftest.py``)
purely as a fast logic harness for the double-entry rules. SQLite is **not** a
proxy for PostgreSQL and these tests are **not** evidence of PostgreSQL
compatibility. The following are exercised only by the SQLite harness and remain
**unverified against PostgreSQL** until the Alembic migration is applied to
Supabase and an integration run is performed:

* PostgreSQL native ENUM types (account_type / entry_source / entry_status);
* ``NUMERIC(18, 2)`` precision/rounding semantics;
* the per-line CHECK constraints as emitted for PostgreSQL;
* concurrent ``entry_number`` uniqueness under real transaction isolation.

The Pydantic schema tests (``test_schemas.py``) are database-independent.
"""
