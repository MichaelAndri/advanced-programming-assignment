"""The ticket and dependencies business logic"""

from __future__ import annotations
from ticket_tracker.models import Ticket
from ticket_tracker.repositories import TicketRepository
from ticket_tracker.schemas import TicketCreate, TicketRead


class TicketService:
    """ticket CRUD and dependency rules"""

    def __init__(self, repository: TicketRepository) -> None:
        self.repository = repository
        self.session = repository.session

    def create_ticket(self, payload: TicketCreate) -> TicketRead:
        """Create and store a ticket"""

        ticket = Ticket(
            title=payload.title,
            description=payload.description,
            status=payload.status.value,
            priority=int(payload.priority),
            estimate_points=payload.estimate_points,
            assignee=payload.assignee,
            tags=payload.tags,
        )
        self.repository.add(ticket)
        self.session.commit()
        return TicketRead.from_model(ticket)

    def list_tickets(self) -> list[TicketRead]:
        """Return all tickets """

        return [TicketRead.from_model(ticket) for ticket in self.repository.list()]
