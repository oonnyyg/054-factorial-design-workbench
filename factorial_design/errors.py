"""Errors raised for invalid design configuration."""


class ConfigError(ValueError):
    """Configuration problem with a JSON-pointer-like location."""

    def __init__(self, message: str, location: str = ""):
        if location:
            full = f"{location}: {message}"
        else:
            full = message
        super().__init__(full)
        self.message = message
        self.location = location
