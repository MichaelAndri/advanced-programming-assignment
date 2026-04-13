from __future__ import annotations
import pytest
from pydantic import ValidationError as PydanticValidationError
from ticket_tracker.schemas import TicketCreate, TicketUpdate


def test_ticket_create_rejects_non_positive_estimate_points() -> None:
    """Estimate points must be greater than zero."""

    with pytest.raises(PydanticValidationError):
        TicketCreate(title="Invalid ticket", estimate_points=0)


def test_ticket_create_normalizes_tags() -> None:
    """Tags should be trimmed and deduplicated."""

    payload = TicketCreate(title="Normalize tags", tags=[" api ", "api", "backend", ""])
    assert payload.tags == ["api", "backend"]


def test_ticket_update_rejects_blank_title() -> None:
    """Blank update titles should be rejected."""

    with pytest.raises(PydanticValidationError):
        TicketUpdate(title="   ")
