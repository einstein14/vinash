"""SQLAlchemy models."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AnonymousUser(Base):
    __tablename__ = "anonymous_users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    thoughts: Mapped[list["Thought"]] = relationship(back_populates="owner")


class Thought(Base):
    __tablename__ = "thoughts"
    __table_args__ = (
        Index("idx_thoughts_user_status_created", "anonymous_user_id", "status", "created_at"),
        Index("idx_thoughts_user_revisit", "anonymous_user_id", "revisit_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    anonymous_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("anonymous_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revisit_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    owner: Mapped[AnonymousUser] = relationship(back_populates="thoughts")
    action: Mapped["Action | None"] = relationship(
        back_populates="thought",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Action(Base):
    __tablename__ = "actions"
    __table_args__ = (UniqueConstraint("thought_id", name="uq_actions_thought_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    thought_id: Mapped[int] = mapped_column(
        ForeignKey("thoughts.id", ondelete="CASCADE"),
        nullable=False,
    )
    action_text: Mapped[str] = mapped_column(Text, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    thought: Mapped[Thought] = relationship(back_populates="action")
