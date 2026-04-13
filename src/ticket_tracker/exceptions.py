"""Eexceptions used throughtout the application"""


class TrackerError(Exception):
    """Base exception for the ticket tracker."""


class TicketNotFoundError(TrackerError):
    """Raised when a ticket does not exist."""


class DependencyError(TrackerError):
    """Raised when a dependency rule is violated."""


class SelfDependencyError(DependencyError):
    """Raised when a ticket is made to depend on itself."""


class CircularDependencyError(DependencyError):
    """Raised when a dependency change introduces a cycle."""


class ValidationError(TrackerError):
    """Raised when domain validation fails."""
