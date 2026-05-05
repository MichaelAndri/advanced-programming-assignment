"""Dependency graph helpers."""

from __future__ import annotations
from collections.abc import Iterable
from ticket_tracker.models import Ticket
from ticket_tracker.schemas import TicketStatus


def build_dependency_graph(tickets: Iterable[Ticket]) -> dict[str, set[str]]:
    """Build an adjacency map of ticket id to dependency ids."""

    graph: dict[str, set[str]] = {}
    for ticket in tickets:
        graph[ticket.ticket_id] = {
            dependency.ticket_id for dependency in ticket.dependencies
        }
    return graph


def is_blocked(ticket: Ticket) -> bool:
    """Return whether a ticket has any unfinished dependencies."""

    return any(
        dependency.status != TicketStatus.DONE.value
        for dependency in ticket.dependencies
    )


def find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Find dependency cycles in an adjacency map/matrix.

    see: https://en.wikipedia.org/wiki/Depth-first_search#Finding_strongly_connected_components
    """

    cycles: list[list[str]] = []
    seen_nodes: set[str] = set()
    stack: list[str] = []
    stack_index: dict[str, int] = {}
    seen_cycles: set[tuple[str, ...]] = set()

    def normalise_cycle(cycle: list[str]) -> tuple[str, ...]:
        # Rotate the cycle so equivalent loops compare as the  same tuple
        cycle_nodes = cycle[:-1]
        rotations = [
            tuple(cycle_nodes[index:] + cycle_nodes[:index])
            for index in range(len(cycle_nodes))
        ]
        return min(rotations)

    def dfs(node: str) -> None:
        seen_nodes.add(node)
        stack_index[node] = len(stack)
        stack.append(node)

        for neighbor in sorted(graph.get(node, set())):
            if neighbor not in seen_nodes:
                dfs(neighbor)
                continue

            if neighbor in stack_index:
                # A backedge means the current path has looped back on itself.
                cycle = stack[stack_index[neighbor] :] + [neighbor]
                normalised = normalise_cycle(cycle)
                if normalised not in seen_cycles:
                    seen_cycles.add(normalised)
                    cycles.append(list(normalised) + [normalised[0]])

        stack.pop()
        stack_index.pop(node, None)

    for node in sorted(graph):
        if node not in seen_nodes:
            dfs(node)

    return cycles
