"""Blocked ticket tests."""

from __future__ import annotations
from ticket_tracker.schemas import TicketCreate, TicketStatus
from ticket_tracker.services import TicketService


def test_list_blocked_tickets_returns_tickets_with_open_dependencies(
    ticket_service: TicketService,
) -> None:
    """Tickets with unfinished dependencies should be listed as blocked."""

    dependency = ticket_service.create_ticket(TicketCreate(title="Backend work"))
    blocked = ticket_service.create_ticket(TicketCreate(title="Frontend work"))

    ticket_service.add_dependency(blocked.ticket_id, dependency.ticket_id)

    blocked_tickets = ticket_service.list_blocked_tickets()
    assert [ticket.ticket_id for ticket in blocked_tickets] == [blocked.ticket_id]


def test_done_dependencies_do_not_block_tickets(ticket_service: TicketService) -> None:
    """Completed dependencies should not leave a ticket blocked."""

    dependency = ticket_service.create_ticket(
        TicketCreate(title="Done work", status=TicketStatus.DONE)
    )
    ticket = ticket_service.create_ticket(TicketCreate(title="Ready work"))

    ticket_service.add_dependency(ticket.ticket_id, dependency.ticket_id)

    blocked_tickets = ticket_service.list_blocked_tickets()
    assert blocked_tickets == []
