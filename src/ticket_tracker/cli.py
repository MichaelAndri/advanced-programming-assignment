"""Typer CLI entry point"""

from __future__ import annotations
from collections.abc import Callable
from typing import Annotated
import typer
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import Engine
from ticket_tracker.database import (
    DEFAULT_DB_URL,
    create_db_engine,
    init_db,
    session_scope,
)
from ticket_tracker.exceptions import TrackerError
from ticket_tracker.repositories import TicketRepository
from ticket_tracker.schemas import TicketCreate, TicketStatus, TicketUpdate
from ticket_tracker.services import SprintPlannerService, TicketService

app = typer.Typer(help="A CLI based ticket tracker and sprint planner application.")


def parse_tags(tags: str) -> list[str]:
    """parse a comma separated tag string"""

    if not tags.strip():
        return []
    return [tag.strip() for tag in tags.split(",")]


def get_ticket_service(database_url: str | None = None) -> TicketService:
    """Create a ticket service for the current command"""

    raise RuntimeError("This helper is not intended to be called directly.")


def format_error(error: Exception) -> str:
    """Convert known exceptions into user-friendly CLI output"""

    if isinstance(error, PydanticValidationError):
        return error.errors()[0]["msg"]
    return str(error)


def run_ticket_command(handler: Callable[[Engine], None]) -> None:
    """Run CLI handler inside an initialised database session"""

    engine = create_db_engine(DEFAULT_DB_URL)
    init_db(engine=engine)
    try:
        handler(engine)
    except (TrackerError, PydanticValidationError) as error:
        typer.echo(f"Error: {format_error(error)}")
        raise typer.Exit(code=1) from error
    finally:
        engine.dispose()


def print_ticket(ticket: dict) -> None:
    """print ticket data in a nice layout"""

    typer.echo(
        f"{ticket['ticket_id']} | {ticket['title']} | status={ticket['status']} | priority={ticket['priority']}"
    )
    typer.echo(
        f"  estimate={ticket['estimate_points']} assignee={ticket['assignee']} tags={','.join(ticket['tags']) or '-'}"
    )
    typer.echo(f"  dependencies={','.join(ticket['dependencies']) or '-'}")


@app.command("create-ticket")
def create_ticket(
    title: Annotated[str, typer.Option(help="Ticket title.")],
    description: Annotated[str, typer.Option(help="Ticket description.")] = "",
    status: Annotated[
        TicketStatus, typer.Option(help="Ticket status.")
    ] = TicketStatus.TODO,
    priority: Annotated[
        int, typer.Option(help="Priority: 1 low, 2 medium, 3 high.")
    ] = 2,
    estimate_points: Annotated[int, typer.Option(help="Story points estimate.")] = 1,
    assignee: Annotated[str | None, typer.Option(help="Assignee name.")] = None,
    tags: Annotated[str, typer.Option(help="Comma-separated tags.")] = "",
) -> None:
    """Create a ticket."""

    def handler(engine: Engine) -> None:
        with session_scope(engine=engine) as session:
            service = TicketService(TicketRepository(session))
            ticket = service.create_ticket(
                TicketCreate(
                    title=title,
                    description=description,
                    status=status,
                    priority=priority,
                    estimate_points=estimate_points,
                    assignee=assignee,
                    tags=parse_tags(tags),
                )
            )
            print_ticket(ticket.model_dump(mode="json"))

    run_ticket_command(handler)


@app.command("list-tickets")
def list_tickets() -> None:
    """List all tickets."""

    def handler(engine: Engine) -> None:
        with session_scope(engine=engine) as session:
            service = TicketService(TicketRepository(session))
            tickets = service.list_tickets()
            if not tickets:
                typer.echo("No tickets found.")
                return
            for ticket in tickets:
                print_ticket(ticket.model_dump(mode="json"))

    run_ticket_command(handler)


@app.command("update-ticket")
def update_ticket(
    ticket_id: str,
    title: Annotated[str | None, typer.Option(help="Updated title.")] = None,
    description: Annotated[
        str | None, typer.Option(help="Updated description.")
    ] = None,
    status: Annotated[TicketStatus | None, typer.Option(help="Updated status.")] = None,
    priority: Annotated[int | None, typer.Option(help="Updated priority.")] = None,
    estimate_points: Annotated[
        int | None, typer.Option(help="Updated estimate.")
    ] = None,
    assignee: Annotated[str | None, typer.Option(help="Updated assignee.")] = None,
    tags: Annotated[
        str | None, typer.Option(help="Updated comma-separated tags.")
    ] = None,
) -> None:
    """Update an existing ticket."""

    def handler(engine: Engine) -> None:
        with session_scope(engine=engine) as session:
            service = TicketService(TicketRepository(session))
            ticket = service.update_ticket(
                ticket_id,
                TicketUpdate(
                    title=title,
                    description=description,
                    status=status,
                    priority=priority,
                    estimate_points=estimate_points,
                    assignee=assignee,
                    tags=parse_tags(tags) if tags is not None else None,
                ),
            )
            print_ticket(ticket.model_dump(mode="json"))

    run_ticket_command(handler)


@app.command("delete-ticket")
def delete_ticket(ticket_id: str) -> None:
    """Delete a ticket."""

    def handler(engine: Engine) -> None:
        with session_scope(engine=engine) as session:
            service = TicketService(TicketRepository(session))
            service.delete_ticket(ticket_id)
            typer.echo(f"Deleted ticket {ticket_id}")

    run_ticket_command(handler)


@app.command("add-dependency")
def add_dependency(ticket_id: str, dependency_id: str) -> None:
    """Add a dependency to a ticket."""

    def handler(engine: Engine) -> None:
        with session_scope(engine=engine) as session:
            service = TicketService(TicketRepository(session))
            ticket = service.add_dependency(ticket_id, dependency_id)
            print_ticket(ticket.model_dump(mode="json"))

    run_ticket_command(handler)


@app.command("list-blocked")
def list_blocked() -> None:
    """List tickets blocked by unfinished dependencies."""

    def handler(engine: Engine) -> None:
        with session_scope(engine=engine) as session:
            service = TicketService(TicketRepository(session))
            tickets = service.list_blocked_tickets()
            if not tickets:
                typer.echo("No blocked tickets found.")
                return
            for ticket in tickets:
                print_ticket(ticket.model_dump(mode="json"))

    run_ticket_command(handler)


@app.command("detect-cycles")
def detect_cycles() -> None:
    """Detect circular dependencies."""

    def handler(engine: Engine) -> None:
        with session_scope(engine=engine) as session:
            service = TicketService(TicketRepository(session))
            cycles = service.detect_cycles()
            if not cycles:
                typer.echo("No dependency cycles detected.")
                return
            for cycle in cycles:
                typer.echo(" -> ".join(cycle))

    run_ticket_command(handler)


@app.command("plan-sprint")
def plan_sprint(capacity: int) -> None:
    """Generate a sprint plan for the provided capacity."""

    def handler(engine: Engine) -> None:
        with session_scope(engine=engine) as session:
            planner = SprintPlannerService(TicketRepository(session))
            plan = planner.plan_sprint(capacity)
            typer.echo(
                f"capacity={plan.capacity} total_points={plan.total_points} remaining_capacity={plan.remaining_capacity}"
            )
            if not plan.tickets:
                typer.echo("No tickets selected.")
                return
            for ticket in plan.tickets:
                typer.echo(
                    f"{ticket.ticket_id} | {ticket.title} | priority={ticket.priority} | estimate={ticket.estimate_points}"
                )

    run_ticket_command(handler)


if __name__ == "__main__":
    app()
