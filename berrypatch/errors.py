class BerryError(Exception):
    """Base error type."""


class FileNotFound(BerryError):
    """File was given that does not exist."""


class AppNotFound(BerryError):
    """File was given that does not exist."""


class InstanceNotFound(BerryError):
    """This app is not installed."""


class CommandFailed(BerryError):
    def __init__(self, result, message=None):
        super(CommandFailed, self).__init__(
            message or f"Command failed with status {result.returncode}"
        )
        self.result = result
