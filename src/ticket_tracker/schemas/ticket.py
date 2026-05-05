"""Pydantic schemas for tickets and sprint plans."""

from __future__ import annotations
from datetime import datetime
from enum import Enum, IntEnum
from pydantic import BaseModel, ConfigDict, Field, field_validator
from ticket_tracker.models import Ticket


class TicketStatus(str, Enum):
    """Supported ticket states."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TicketPriority(IntEnum):
    """Ticket priority levels."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


def _normalise_tags(tags: list[str] | None) -> list[str] | None:
    """Trim whitespace and remove duplicate tags while preserving order."""

    if tags is None:
        return None

    seen: set[str] = set()
    normalised: list[str] = []
    for tag in tags:
        cleaned = tag.strip()
        # Preserve the first occurrence so user input order is kept stable
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            normalised.append(cleaned)
    return normalised


class TicketCreate(BaseModel):
    """Payload used to create a ticket."""

    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    status: TicketStatus = TicketStatus.TODO
    priority: TicketPriority = TicketPriority.MEDIUM
    estimate_points: int = Field(default=1, ge=1)
    assignee: str | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        """Normalise title whitespace."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("title must not be blank")
        return stripped

    @field_validator("priority", mode="before")
    @classmethod
    def validate_priority(cls, value: TicketPriority | int) -> TicketPriority:
        """Ensure priority values are valid"""
        try:
            return TicketPriority(value)
        except ValueError as exc:
            raise ValueError(
                "Priority must be 1 (low), 2 (medium), or 3 (high)."
            ) from exc

    @field_validator("tags", mode="before")
    @classmethod
    def normalise_tags(cls, value: list[str] | None) -> list[str]:
        """Normalise tag values before validation."""

        return _normalise_tags(value) or []


class TicketUpdate(BaseModel):
    """Partial payload used to update an existing ticket."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    estimate_points: int | None = Field(default=None, ge=1)
    assignee: str | None = None
    tags: list[str] | None = None

    @field_validator("title")
    @classmethod
    def strip_optional_title(cls, value: str | None) -> str | None:
        """Normalise title whitespace when present."""

        if value is None:
            return None

        stripped = value.strip()
        if not stripped:
            raise ValueError("title must not be blank")
        return stripped

    @field_validator("tags", mode="before")
    @classmethod
    def normalise_optional_tags(cls, value: list[str] | None) -> list[str] | None:
        """Normalise tags when tags are updated."""

        return _normalise_tags(value)

    @field_validator("priority", mode="before")
    @classmethod
    def validate_optional_priority(
        cls, value: TicketPriority | int | None
    ) -> TicketPriority | None:
        """Ensure optional priority values still match the enum"""

        if value is None:
            return None
        try:
            return TicketPriority(value)
        except ValueError as exc:
            raise ValueError(
                "Priority must be 1 (low), 2 (medium), or 3 (high)."
            ) from exc


class TicketRead(BaseModel):
    """Serialized ticket response."""

    model_config = ConfigDict(from_attributes=True)

    ticket_id: str
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    estimate_points: int
    assignee: str | None
    tags: list[str]
    dependencies: list[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, ticket: Ticket) -> "TicketRead":
        """Convert a SQLAlchemy ticket model to a schema."""

        return cls(
            ticket_id=ticket.ticket_id,
            title=ticket.title,
            description=ticket.description,
            status=TicketStatus(ticket.status),
            priority=TicketPriority(ticket.priority),
            estimate_points=ticket.estimate_points,
            assignee=ticket.assignee,
            tags=list(ticket.tags or []),
            # Sort related ids so CLI and tests get stable output.
            dependencies=sorted(
                dependency.ticket_id for dependency in ticket.dependencies
            ),
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
        )


class SprintPlanItem(BaseModel):
    """A single sprint-ready ticket in the plan."""

    ticket_id: str
    title: str
    priority: TicketPriority
    estimate_points: int
    dependencies: list[str]

    @classmethod
    def from_model(cls, ticket: Ticket) -> "SprintPlanItem":
        """Build a sprint plan item from a ticket model."""

        return cls(
            ticket_id=ticket.ticket_id,
            title=ticket.title,
            priority=TicketPriority(ticket.priority),
            estimate_points=ticket.estimate_points,
            # Dependency ids are serialised in a predictable order.
            dependencies=sorted(
                dependency.ticket_id for dependency in ticket.dependencies
            ),
        )


class SprintPlan(BaseModel):
    """Output for a sprint planning run."""

    capacity: int
    total_points: int
    remaining_capacity: int
    tickets: list[SprintPlanItem]
