"""Database helpers for ticket tracker."""

from __future__ import annotations
import os
from contextlib import contextmanager
from typing import Iterator
from sqlalchemy import Engine, event, create_engine
from sqlalchemy.engine import Connection
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DB_URL = os.getenv("TICKET_TRACKER_DB_URL", "sqlite:///ticket_tracker.db")


class Base(DeclarativeBase):
    """Base declarative class for SQLAlchemy models."""


def create_db_engine(database_url: str | None = None) -> Engine:
    """Create a database engine with SQLite foreign keys enabled."""

    resolved_url = database_url or DEFAULT_DB_URL
    connect_args = {"check_same_thread": False} if resolved_url.startswith("sqlite") else {}
    engine = create_engine(resolved_url, connect_args=connect_args, future=True)

    if resolved_url.startswith("sqlite"):
        _enable_sqlite_foreign_keys(engine)

    return engine


def _enable_sqlite_foreign_keys(engine: Engine) -> None:
    """Turn on foreign key enforcement for SQLite connections."""

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection: Connection, _: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    """Build a configured session factory."""

    engine = create_db_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db(engine: Engine | None = None, database_url: str | None = None) -> Engine:
    """Create database tables if they do not already exist."""

    from ticket_tracker.models import ticket as _ticket_models

    resolved_engine = engine or create_db_engine(database_url)
    Base.metadata.create_all(bind=resolved_engine)
    return resolved_engine


@contextmanager
def session_scope(database_url: str | None = None) -> Iterator[Session]:
    """Yield a transactional session and close it afterwards."""

    session = create_session_factory(database_url)()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
