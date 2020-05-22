class BerryError(Exception):
    """Base error type."""


class FileNotFound(BerryError):
    """File was given that does not exist."""


class AppNotFound(BerryError):
    """File was given that does not exist."""
