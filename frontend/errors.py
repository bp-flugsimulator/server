"""
This module holds all error classes which are used in the frontend.
"""
from server.errors import FsimError


class SlaveOfflineError(FsimError):
    """
    Base class for slave offline Exception's.
    """

    def __init__(self, name, type, slave, action):
        super().__init__(
            "Could not {action} on {type} `{name}` because the client `{slave}` is offline.".
            format(name=name, type=type, slave=slave, action=action))


class FilesystemError(FsimError):
    """
    Base class for all FilesystemError's
    """

    def __init__(self, name, slave, message):
        if message is None:
            message = "An error ocurred in the Filesystem model."

        super().__init__(message)
        self.name = name
        self.slave = slave


class FilesystemMovedError(FilesystemError):
    """
    If the filesystem is already moved.
    """

    def __init__(self, name, slave):
        super().__init__(
            name, slave,
            "Could not move Filesystem `{}` on client `{}` because it is already moved.".
            format(name, slave))


class FilesystemNotMovedError(FilesystemError):
    """
    If the filesystem is already moved.
    """

    def __init__(self, name, slave):
        super().__init__(
            name, slave,
            "Could not restore Filesystem `{}` on client `{}` because it is not moved.".
            format(name, slave))


class FilesystemDeleteError(FilesystemError):
    """
    If the filesystem is moved then it can not be deleted.
    """

    def __init__(self, name, slave):
        super().__init__(
            name, slave,
            "Can not delete filesystem `{}` on client `{}` because it is still moved. Restore the filesystem and try again.".
            format(name, slave))
