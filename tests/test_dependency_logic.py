from __future__ import annotations
import pytest
from ticket_tracker.exceptions import SelfDependencyError, TicketNotFoundError
from ticket_tracker.schemas import TicketCreate
from ticket_tracker.services import TicketService


def test_add_dependency_rejects_self_dependency(ticket_service: TicketService) -> None:
    """A ticket cannot depend on itself."""

    ticket = ticket_service.create_ticket(TicketCreate(title="Self dependency"))

    with pytest.raises(SelfDependencyError):
        ticket_service.add_dependency(ticket.ticket_id, ticket.ticket_id)


def test_add_dependency_rejects_missing_dependency(
    ticket_service: TicketService,
) -> None:
    """Dependencies must reference an existing ticket."""

    ticket = ticket_service.create_ticket(TicketCreate(title="Existing ticket"))

    with pytest.raises(TicketNotFoundError):
        ticket_service.add_dependency(ticket.ticket_id, "missing-ticket-id")
