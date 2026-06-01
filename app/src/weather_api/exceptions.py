"""Domain errors raised by weather providers and upstream HTTP clients."""


class LocationValidationError(Exception):
    """Raised when weather location query parameters fail validation."""

    def __init__(self, message: str) -> None:
        """Store a human-readable validation failure message."""
        super().__init__(message)
        self.message = message


class LocationNotFoundError(Exception):
    """Raised when upstream cannot resolve the requested location."""

    def __init__(self, message: str) -> None:
        """Store a human-readable not-found message."""
        super().__init__(message)
        self.message = message


class UpstreamWeatherError(Exception):
    """Raised when upstream weather service fails or returns invalid data."""

    def __init__(self, message: str) -> None:
        """Store a human-readable upstream failure message."""
        super().__init__(message)
        self.message = message


class UpstreamRateLimitError(Exception):
    """Raised when upstream weather service rate-limits the request."""

    def __init__(self, message: str) -> None:
        """Store a human-readable rate-limit message."""
        super().__init__(message)
        self.message = message
