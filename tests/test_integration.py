"""Integration tests to make sure everything works together"""

import re
from typer.testing import CliRunner
from ticket_tracker.cli import app

runner = CliRunner()


def test_create_ticket():
    result = runner.invoke(
        app, ["create-ticket", "--title", "My Test Ticket", "--priority", "2"]
    )
    print(result.stdout)
    print(result.exception)
    assert result.exit_code == 0
    assert "priority=2" in result.output
    assert "My Test Ticket" in result.output


def test_create_ticket_rejects_invalid_priority():
    result = runner.invoke(
        app, ["create-ticket", "--title", "Invalid Priority", "--priority", "5"]
    )
    print(result.stdout)
    print(result.exception)
    assert result.exit_code == 1
    assert "Priority must be 1 (low), 2 (medium), or 3 (high)." in result.output


def test_list_tickets():
    # Create a ticket first
    runner.invoke(
        app, ["create-ticket", "--title", "List Test Ticket", "--priority", "1"]
    )

    result = runner.invoke(app, ["list-tickets"])
    print(result.stdout)
    print(result.exception)
    assert result.exit_code == 0
    assert "List Test Ticket" in result.output


def test_list_blocked_tickets():
    # Create two tickets with a dependency
    result_a = runner.invoke(
        app, ["create-ticket", "--title", "Blocked Dependency", "--priority", "1"]
    )
    result_b = runner.invoke(
        app, ["create-ticket", "--title", "Blocked Ticket", "--priority", "1"]
    )
    print(result_a.stdout)
    print(result_a.exception)
    print(result_b.stdout)
    print(result_b.exception)
    assert result_a.exit_code == 0
    assert result_b.exit_code == 0

    # Extract the ticket IDs
    match_a = re.search(r"^\S+", result_a.stdout)
    match_b = re.search(r"^\S+", result_b.stdout)
    assert match_a is not None
    assert match_b is not None
    ticket_id_a = match_a.group(0)
    ticket_id_b = match_b.group(0)

    # Add a dependency from B to A
    dep_result = runner.invoke(app, ["add-dependency", ticket_id_b, ticket_id_a])
    print(dep_result.stdout)
    print(dep_result.exception)
    assert dep_result.exit_code == 0

    # List blocked tickets and verify the blocked one appears
    list_result = runner.invoke(app, ["list-blocked"])
    print(list_result.stdout)
    print(list_result.exception)
    assert list_result.exit_code == 0
    assert ticket_id_a in list_result.output
    assert ticket_id_b in list_result.output


def test_update_ticket():
    # Create a ticket first
    create_result = runner.invoke(
        app, ["create-ticket", "--title", "Update Test Ticket", "--priority", "1"]
    )
    print(create_result.stdout)
    print(create_result.exception)
    assert create_result.exit_code == 0

    # Extract the ticket ID from the created ticket output
    m = re.search(r"^\S+", create_result.stdout)
    assert m is not None
    ticket_id = m.group(0)

    # Update the ticket's title and priority
    update_result = runner.invoke(
        app,
        [
            "update-ticket",
            ticket_id,
            "--title",
            "Updated Test Ticket",
            "--priority",
            "3",
        ],
    )
    print(update_result.stdout)
    print(update_result.exception)
    assert update_result.exit_code == 0
    assert "Updated Test Ticket" in update_result.output
    assert "priority=3" in update_result.output


def test_add_dependency():
    # Create two tickets
    result_a = runner.invoke(
        app, ["create-ticket", "--title", "Dependency A", "--priority", "1"]
    )
    result_b = runner.invoke(
        app, ["create-ticket", "--title", "Dependency B", "--priority", "1"]
    )
    print(result_a.stdout)
    print(result_a.exception)
    print(result_b.stdout)
    print(result_b.exception)
    assert result_a.exit_code == 0
    assert result_b.exit_code == 0

    # Extract the ticket IDs
    m_a = re.search(r"^\S+", result_a.stdout)
    m_b = re.search(r"^\S+", result_b.stdout)
    assert m_a is not None
    assert m_b is not None
    ticket_id_a = m_a.group(0)
    ticket_id_b = m_b.group(0)

    # Add a dependency from A to B
    dep_result = runner.invoke(app, ["add-dependency", ticket_id_a, ticket_id_b])
    print(dep_result.stdout)
    print(dep_result.exception)
    assert dep_result.exit_code == 0


def test_add_dependency_rejects_self_dependency():
    # Create a ticket
    result = runner.invoke(
        app, ["create-ticket", "--title", "Self Dependency", "--priority", "1"]
    )
    print(result.stdout)
    print(result.exception)
    assert result.exit_code == 0

    # Extract the ticket ID
    m = re.search(r"^\S+", result.stdout)
    assert m is not None
    ticket_id = m.group(0)

    # Attempt to add a self dependency
    dep_result = runner.invoke(app, ["add-dependency", ticket_id, ticket_id])
    print(dep_result.stdout)
    print(dep_result.exception)
    assert dep_result.exit_code == 1
    assert "A ticket cannot depend on itself." in dep_result.output


def test_delete_ticket():
    # Create a ticket
    result = runner.invoke(
        app, ["create-ticket", "--title", "Delete Test Ticket", "--priority", "1"]
    )
    print(result.stdout)
    print(result.exception)
    assert result.exit_code == 0

    # Extract the ticket ID
    m = re.search(r"^\S+", result.stdout)
    assert m is not None
    ticket_id = m.group(0)

    # Delete the ticket
    delete_result = runner.invoke(app, ["delete-ticket", ticket_id])
    print(delete_result.stdout)
    print(delete_result.exception)
    assert delete_result.exit_code == 0

    # Verify the ticket no longer appears in the list
    list_result = runner.invoke(app, ["list-tickets"])
    print(list_result.stdout)
    print(list_result.exception)
    assert list_result.exit_code == 0
    assert "Delete Test Ticket" not in list_result.output


def test_sprint_plan_success():
    # Create tickets with dependencies
    result_a = runner.invoke(
        app,
        [
            "create-ticket",
            "--title",
            "Sprint A",
            "--priority",
            "3",
            "--estimate-points",
            "5",
        ],
    )
    result_b = runner.invoke(
        app,
        [
            "create-ticket",
            "--title",
            "Sprint B",
            "--priority",
            "2",
            "--estimate-points",
            "3",
        ],
    )
    print(result_a.stdout)
    print(result_a.exception)
    print(result_b.stdout)
    print(result_b.exception)
    assert result_a.exit_code == 0
    assert result_b.exit_code == 0

    # Extract the ticket IDs
    m_a = re.search(r"^\S+", result_a.stdout)
    m_b = re.search(r"^\S+", result_b.stdout)
    assert m_a is not None
    assert m_b is not None
    ticket_id_a = m_a.group(0)
    ticket_id_b = m_b.group(0)

    # Add a dependency from A to B
    dep_result = runner.invoke(app, ["add-dependency", ticket_id_a, ticket_id_b])
    print(dep_result.stdout)
    print(dep_result.exception)
    assert dep_result.exit_code == 0

    # Plan a sprint with enough capacity for both tickets
    plan_result = runner.invoke(app, ["plan-sprint", "10"])
    print(plan_result.stdout)
    print(plan_result.exception)
    assert plan_result.exit_code == 0
    assert "capacity=10" in plan_result.output
    assert "remaining_capacity" in plan_result.output
    assert "total_points" in plan_result.output
