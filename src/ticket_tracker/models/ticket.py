"""SQLAlchemy ticket models."""

from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Table, Text, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ticket_tracker.database import Base


def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


ticket_dependencies = Table(
    "ticket_dependencies",
    Base.metadata,
    Column(
        "ticket_id",
        String(36),
        ForeignKey("tickets.ticket_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "dependency_id",
        String(36),
        ForeignKey("tickets.ticket_id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Ticket(Base):
    """A work item that may depend on other tickets."""

    __tablename__ = "tickets"

    ticket_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="todo", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    estimate_points: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    assignee: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    dependencies: Mapped[list["Ticket"]] = relationship(
        "Ticket",
        secondary=ticket_dependencies,
        primaryjoin=ticket_id == ticket_dependencies.c.ticket_id,
        secondaryjoin=ticket_id == ticket_dependencies.c.dependency_id,
        backref="dependents",
        lazy="selectin",
    )
