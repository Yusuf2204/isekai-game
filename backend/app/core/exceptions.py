"""Custom application exceptions."""


class GameError(Exception):
    """Base exception for game-related errors."""

    def __init__(
        self, message: str, code: str = "GAME_ERROR", details: dict | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class ValidationError(GameError):
    """Raised when input validation fails."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message, code="VALIDATION_ERROR", details=details)


class NotFoundError(GameError):
    """Raised when a resource is not found."""

    def __init__(self, resource: str, identifier: str | int) -> None:
        super().__init__(
            f"{resource} not found: {identifier}",
            code="NOT_FOUND",
            details={"resource": resource, "identifier": str(identifier)},
        )


class ConflictError(GameError):
    """Raised when a state conflict occurs."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message, code="CONFLICT", details=details)


class GameStateError(GameError):
    """Raised when an invalid game state transition is attempted."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message, code="INVALID_STATE", details=details)


class ResourceError(ValidationError):
    """Raised when a resource validation fails."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message, details=details)
