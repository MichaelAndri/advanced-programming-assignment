from __future__ import annotations
import pytest
from typer.testing import CliRunner
from ticket_tracker import cli
from ticket_tracker.database import (
    create_db_engine,
    create_session_factory,
    init_db,
    session_scope,
)
from ticket_tracker.models import Ticket


runner = CliRunner()


def _use_temp_database(monkeypatch, tmp_path) -> str:
    database_url = f"sqlite:///{tmp_path / 'cli-test.db'}"
    monkeypatch.setattr(cli, "DEFAULT_DB_URL", database_url)
    return database_url


def test_get_ticket_service_raises_runtime_error() -> None:
    """The direct helper should not be callable."""

    try:
        cli.get_ticket_service()
    except RuntimeError as error:
        assert str(error) == "This helper is not intended to be called directly."
    else:
        raise AssertionError("Expected get_ticket_service() to raise RuntimeError")


def test_format_error_returns_plain_exception_message() -> None:
    """Unknown errors should fall back to their string value"""

    assert cli.format_error(ValueError("plain failure")) == "plain failure"


def test_parse_tags_strips_each_tag() -> None:
    """Tag parsing should preserve items while trimming whitespace."""

    assert cli.parse_tags(" backend, api ,urgent ") == ["backend", "api", "urgent"]


def test_list_tickets_prints_empty_message(monkeypatch, tmp_path) -> None:
    """Listing tickets on an empty database should print a helpful message."""

    _use_temp_database(monkeypatch, tmp_path)

    result = runner.invoke(cli.app, ["list-tickets"])

    assert result.exit_code == 0
    assert "No tickets found." in result.output


def test_list_blocked_prints_empty_message(monkeypatch, tmp_path) -> None:
    """Blocked ticket listing should handle an empty database"""

    _use_temp_database(monkeypatch, tmp_path)

    result = runner.invoke(cli.app, ["list-blocked"])

    assert result.exit_code == 0
    assert "No blocked tickets found." in result.output


def test_detect_cycles_prints_detected_cycle(monkeypatch, tmp_path) -> None:
    """Cycle detection should print the discovered dependency path."""

    database_url = _use_temp_database(monkeypatch, tmp_path)
    engine = create_db_engine(database_url)
    init_db(engine=engine)

    with session_scope(engine=engine) as session:
        ticket_a = Ticket(title="Cycle A", estimate_points=1, tags=[])
        ticket_b = Ticket(title="Cycle B", estimate_points=1, tags=[])
        session.add_all([ticket_a, ticket_b])
        session.flush()

        ticket_a.dependencies.append(ticket_b)
        ticket_b.dependencies.append(ticket_a)
        session.commit()

    result = runner.invoke(cli.app, ["detect-cycles"])

    assert result.exit_code == 0
    assert ticket_a.ticket_id in result.output
    assert ticket_b.ticket_id in result.output
    assert " -> " in result.output

    engine.dispose()


def test_detect_cycles_prints_empty_message(monkeypatch, tmp_path) -> None:
    """Cycle detection should explain when no dependency cycles exist."""

    _use_temp_database(monkeypatch, tmp_path)

    result = runner.invoke(cli.app, ["detect-cycles"])

    assert result.exit_code == 0
    assert "No dependency cycles detected." in result.output


def test_plan_sprint_prints_when_no_tickets_selected(monkeypatch, tmp_path) -> None:
    """Sprint planning should explain when nothing fits the requested capacity."""

    _use_temp_database(monkeypatch, tmp_path)

    create_result = runner.invoke(
        cli.app,
        [
            "create-ticket",
            "--title",
            "Too Large",
            "--estimate-points",
            "5",
            "--priority",
            "3",
        ],
    )
    assert create_result.exit_code == 0

    result = runner.invoke(cli.app, ["plan-sprint", "3"])

    assert result.exit_code == 0
    assert "capacity=3" in result.output
    assert "No tickets selected." in result.output


def test_create_session_factory_returns_working_sessions(tmp_path) -> None:
    """The session factory helper should create usable sessions."""

    database_url = f"sqlite:///{tmp_path / 'factory.db'}"
    init_engine = init_db(database_url=database_url)
    session_factory = create_session_factory(database_url)

    try:
        with session_factory() as session:
            assert session.bind is not None
    finally:
        session_factory.kw["bind"].dispose()
        init_engine.dispose()


def test_init_db_creates_engine_from_database_url(tmp_path) -> None:
    """init_db should create and return an engine when only a URL is provided."""

    database_url = f"sqlite:///{tmp_path / 'init.db'}"

    engine = init_db(database_url=database_url)

    try:
        assert engine.url.render_as_string(hide_password=False) == database_url
    finally:
        engine.dispose()


def test_session_scope_disposes_created_engine(monkeypatch, tmp_path) -> None:
    """session_scope should dispose internally created engines."""

    database_url = f"sqlite:///{tmp_path / 'session.db'}"
    disposed = False
    session_closed = False

    class FakeEngine:
        def dispose(self) -> None:
            nonlocal disposed
            disposed = True

    class FakeSession:
        bind = None

        def rollback(self) -> None:
            raise AssertionError(
                "rollback() should not be called on a successful session"
            )

        def close(self) -> None:
            nonlocal session_closed
            session_closed = True

    fake_engine = FakeEngine()
    fake_session = FakeSession()
    fake_session.bind = fake_engine

    def fake_sessionmaker(**kwargs):
        assert kwargs["bind"] is fake_engine

        def factory():
            return fake_session

        return factory

    monkeypatch.setattr(
        "ticket_tracker.database.create_db_engine", lambda _: fake_engine
    )
    monkeypatch.setattr("ticket_tracker.database.sessionmaker", fake_sessionmaker)

    with session_scope(database_url=database_url) as session:
        assert session is fake_session

    assert session_closed is True
    assert disposed is True


def test_session_scope_rolls_back_on_error(monkeypatch) -> None:
    """session_scope should roll back and close the session when an error occurs."""

    rolled_back = False
    session_closed = False

    class FakeSession:
        def rollback(self) -> None:
            nonlocal rolled_back
            rolled_back = True

        def close(self) -> None:
            nonlocal session_closed
            session_closed = True

    fake_session = FakeSession()

    def fake_sessionmaker(**kwargs):
        def factory():
            return fake_session

        return factory

    monkeypatch.setattr("ticket_tracker.database.sessionmaker", fake_sessionmaker)

    with pytest.raises(RuntimeError, match="boom"):
        with session_scope(engine=object()) as session:
            assert session is fake_session
            raise RuntimeError("boom")

    assert rolled_back is True
    assert session_closed is True
