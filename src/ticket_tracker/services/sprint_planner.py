"""Sprint planning service"""

from __future__ import annotations
from ticket_tracker.exceptions import CircularDependencyError, ValidationError
from ticket_tracker.models import Ticket
from ticket_tracker.repositories import TicketRepository
from ticket_tracker.schemas import SprintPlan, SprintPlanItem, TicketStatus
from ticket_tracker.utils.dependency_graph import build_dependency_graph, find_cycles


class SprintPlannerService:
    """Build a sprint plan that respects dependencies and capacity"""

    def __init__(self, repository: TicketRepository) -> None:
        self.repository = repository

    def plan_sprint(self, capacity: int) -> SprintPlan:
        """Select tickets for a sprint using priority and dependency order"""

        if capacity <= 0:
            raise ValidationError("Sprint capacity must be greater than zero.")

        tickets = self.repository.list()
        cycles = find_cycles(build_dependency_graph(tickets))
        if cycles:
            raise CircularDependencyError(
                "Cannot plan a sprint while dependency cycles exist."
            )

        remaining_capacity = capacity
        planned: list[Ticket] = []
        planned_ids: set[str] = set()
        active_tickets = [
            ticket for ticket in tickets if ticket.status != TicketStatus.DONE.value
        ]

        def sort_key(ticket: Ticket) -> tuple[int, int, str, str]:
            return (
                -ticket.priority,
                ticket.estimate_points,
                ticket.created_at.isoformat(),
                ticket.ticket_id,
            )

        def schedule(ticket: Ticket) -> bool:
            nonlocal remaining_capacity

            if (
                ticket.status == TicketStatus.DONE.value
                or ticket.ticket_id in planned_ids
            ):
                return True

            for dependency in sorted(
                [
                    dependency
                    for dependency in ticket.dependencies
                    if dependency.status != TicketStatus.DONE.value
                ],
                key=sort_key,
            ):
                if not schedule(dependency):
                    return False

            if any(
                dependency.status != TicketStatus.DONE.value
                and dependency.ticket_id not in planned_ids
                for dependency in ticket.dependencies
            ):
                return False

            if ticket.estimate_points > remaining_capacity:
                return False

            planned.append(ticket)
            planned_ids.add(ticket.ticket_id)
            remaining_capacity -= ticket.estimate_points
            return True

        for ticket in sorted(active_tickets, key=sort_key):
            schedule(ticket)

        return SprintPlan(
            capacity=capacity,
            total_points=sum(ticket.estimate_points for ticket in planned),
            remaining_capacity=remaining_capacity,
            tickets=[SprintPlanItem.from_model(ticket) for ticket in planned],
        )
