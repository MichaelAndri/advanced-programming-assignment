"""Sprint planning tests."""

from __future__ import annotations

import pytest

from ticket_tracker.exceptions import CircularDependencyError
from ticket_tracker.models import Ticket
from ticket_tracker.schemas import TicketCreate, TicketPriority
from ticket_tracker.services import SprintPlannerService, TicketService


def test_plan_sprint_prioritizes_ticket_and_schedules_dependencies_first(
    ticket_service: TicketService,
    sprint_planner: SprintPlannerService,
) -> None:
    """A high-priority ticket should pull in its dependencies first if they fit."""

    dependency = ticket_service.create_ticket(
        TicketCreate(
            title="Foundation work", priority=TicketPriority.LOW, estimate_points=2
        )
    )
    high_priority = ticket_service.create_ticket(
        TicketCreate(
            title="Critical feature", priority=TicketPriority.HIGH, estimate_points=5
        )
    )
    ticket_service.create_ticket(
        TicketCreate(
            title="Medium ticket", priority=TicketPriority.MEDIUM, estimate_points=4
        )
    )
    ticket_service.add_dependency(high_priority.ticket_id, dependency.ticket_id)

    plan = sprint_planner.plan_sprint(capacity=7)

    assert [ticket.title for ticket in plan.tickets] == [
        "Foundation work",
        "Critical feature",
    ]
    assert plan.total_points == 7
    assert plan.remaining_capacity == 0


def test_plan_sprint_rejects_cycles(
    session, sprint_planner: SprintPlannerService
) -> None:
    """Sprint planning should fail when cycles exist."""

    ticket_a = Ticket(title="A", estimate_points=1, priority=3, tags=[])
    ticket_b = Ticket(title="B", estimate_points=1, priority=2, tags=[])
    session.add_all([ticket_a, ticket_b])
    session.flush()
    ticket_a.dependencies.append(ticket_b)
    ticket_b.dependencies.append(ticket_a)
    session.commit()

    with pytest.raises(CircularDependencyError):
        sprint_planner.plan_sprint(capacity=5)
