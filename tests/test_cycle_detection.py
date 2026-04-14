"""Cycle detection tests."""

from __future__ import annotations

import pytest

from ticket_tracker.exceptions import CircularDependencyError
from ticket_tracker.models import Ticket
from ticket_tracker.schemas import TicketCreate
from ticket_tracker.services import TicketService


def test_add_dependency_rejects_new_cycle(ticket_service: TicketService) -> None:
    """Service should block a change that creates a cycle."""

    ticket_a = ticket_service.create_ticket(TicketCreate(title="A"))
    ticket_b = ticket_service.create_ticket(TicketCreate(title="B"))
    ticket_c = ticket_service.create_ticket(TicketCreate(title="C"))

    ticket_service.add_dependency(ticket_a.ticket_id, ticket_b.ticket_id)
    ticket_service.add_dependency(ticket_b.ticket_id, ticket_c.ticket_id)

    with pytest.raises(CircularDependencyError):
        ticket_service.add_dependency(ticket_c.ticket_id, ticket_a.ticket_id)


def test_detect_cycles_finds_existing_cycle(
    session, ticket_service: TicketService
) -> None:
    """Cycle detection should report cycles already present in the database."""

    ticket_a = Ticket(title="A", estimate_points=1, tags=[])
    ticket_b = Ticket(title="B", estimate_points=1, tags=[])
    ticket_c = Ticket(title="C", estimate_points=1, tags=[])
    session.add_all([ticket_a, ticket_b, ticket_c])
    session.flush()

    ticket_a.dependencies.append(ticket_b)
    ticket_b.dependencies.append(ticket_c)
    ticket_c.dependencies.append(ticket_a)
    session.commit()

    cycles = ticket_service.detect_cycles()
    assert len(cycles) == 1
    assert set(cycles[0][:-1]) == {
        ticket_a.ticket_id,
        ticket_b.ticket_id,
        ticket_c.ticket_id,
    }
