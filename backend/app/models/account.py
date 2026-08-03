"""Account ORM model (chart of accounts).

An account is a bucket in the double-entry ledger. Its ``type`` fixes the
normal (increasing) balance side: ASSET/EXPENSE are debit-normal;
LIABILITY/EQUITY/REVENUE are credit-normal. Accounts are never hard-deleted in
the MVP; deactivate via ``is_active`` instead.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AccountType
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.journal import JournalLine


class Account(TimestampMixin, Base):
    """A single account in the chart of accounts."""

    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    # Short numeric code, e.g. "5100". Unique and required.
    code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[AccountType] = mapped_column(
        SAEnum(AccountType, name="account_type", native_enum=True),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        nullable=False,
        server_default=text("true"),
        default=True,
    )

    lines: Mapped[list[JournalLine]] = relationship(back_populates="account")

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Account {self.code} {self.name} ({self.type.value})>"
