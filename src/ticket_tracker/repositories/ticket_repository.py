"""DB operations for tickets"""

from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from ticket_tracker.models import Ticket


class TicketRepository:
    """DB wrapper"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, ticket: Ticket) -> Ticket:
        """Add a new ticket"""

        self.session.add(ticket)
        self.session.flush()
        return ticket

    def get(self, ticket_id: str) -> Ticket | None:
        """Fetch a ticket by id with dependency data."""

        statement = (
            select(Ticket)
            .options(selectinload(Ticket.dependencies))
            .where(Ticket.ticket_id == ticket_id)
        )
        return self.session.scalars(statement).unique().one_or_none()

    def list(self) -> list[Ticket]:
        """List all tickets ordered by creation time"""

        statement = (
            select(Ticket)
            .options(selectinload(Ticket.dependencies))
            .order_by(Ticket.created_at)
        )
        return list(self.session.scalars(statement).unique().all())

    def delete(self, ticket: Ticket) -> None:
        """Delete a ticket"""

        self.session.delete(ticket)
        self.session.flush()

    def add_dependency(self, ticket: Ticket, dependency: Ticket) -> None:
        """Attach a dependency to a ticket if it is not already linked"""

        if dependency not in ticket.dependencies:
            ticket.dependencies.append(dependency)
            self.session.flush()
