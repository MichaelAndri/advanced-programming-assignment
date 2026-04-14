"""Shared pytest fixtures."""

from __future__ import annotations
import pytest
from sqlalchemy.orm import Session, sessionmaker
from ticket_tracker.database import create_db_engine, init_db
from ticket_tracker.repositories import TicketRepository
from ticket_tracker.services import SprintPlannerService, TicketService


@pytest.fixture
def session(tmp_path) -> Session:
    """Provide a fresh SQLite database session for each test"""

    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_db_engine(database_url)
    init_db(engine=engine)
    session_factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )

    with session_factory() as db_session:
        yield db_session

    engine.dispose()


@pytest.fixture
def ticket_service(session: Session) -> TicketService:
    """Create a ticket service bound to the test session"""

    return TicketService(TicketRepository(session))


@pytest.fixture
def sprint_planner(session: Session) -> SprintPlannerService:
    """Create a sprint planner bound to the test session"""

    return SprintPlannerService(TicketRepository(session))
