"""The ticket and dependencies business logic"""

from __future__ import annotations
from ticket_tracker.models import Ticket
from ticket_tracker.repositories import TicketRepository
from ticket_tracker.schemas import TicketCreate, TicketRead
from ticket_tracker.schemas.ticket import TicketStatus, TicketUpdate
from ticket_tracker.utils.dependency_graph import build_dependency_graph, find_cycles, is_blocked
from ticket_tracker.exceptions import (
    CircularDependencyError,
    SelfDependencyError,
    TicketNotFoundError,
)


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
   
    def update_ticket(self, ticket_id: str, payload: TicketUpdate) -> TicketRead:
        """Update the provided fields for an existing ticket."""
        ticket = self._get_required_ticket(ticket_id)
        updates = payload.model_dump(exclude_none=True)
        for field_name, value in updates.items():
            if field_name == "status":
                setattr(ticket, field_name, value.value)
            elif field_name == "priority":
                setattr(ticket, field_name, int(value))
            else:
                setattr(ticket, field_name, value)
        self.session.commit()
        self.session.refresh(ticket)
        return TicketRead.from_model(ticket)
    def delete_ticket(self, ticket_id: str) -> None:
        """Delete a ticket"""
        ticket = self._get_required_ticket(ticket_id)
        self.repository.delete(ticket)
        self.session.commit()

    def add_dependency(self, ticket_id: str, dependency_id: str) -> TicketRead:
        """Add a dependency between two tickets and enforce rules"""
        if ticket_id == dependency_id:
            raise SelfDependencyError("A ticket cannot depend on itself.")
        ticket = self._get_required_ticket(ticket_id)
        dependency = self._get_required_ticket(dependency_id)
        self.repository.add_dependency(ticket, dependency)
        cycles = self.detect_cycles()
        if cycles:
            self.session.rollback()
            raise CircularDependencyError("Adding this dependency would create a circular dependency.")
        self.session.commit()
        self.session.refresh(ticket)
        return TicketRead.from_model(ticket)
    def list_blocked_tickets(self) -> list[TicketRead]:
        """List tickets with unfinished dependencies"""
        tickets = [
            ticket
            for ticket in self.repository.list()
            if ticket.status != TicketStatus.DONE.value and is_blocked(ticket)
        ]
        return [TicketRead.from_model(ticket) for ticket in tickets]

    def detect_cycles(self) -> list[list[str]]:
        """Detect dependency cycles in the current ticket graph."""
        graph = build_dependency_graph(self.repository.list())
        return find_cycles(graph)

    def _get_required_ticket(self, ticket_id: str) -> Ticket:
        """Fetch a ticket or raise a domain error."""
        ticket = self.repository.get(ticket_id)
        if ticket is None:
            raise TicketNotFoundError(f"Ticket '{ticket_id}' was not found.")
        return ticket
