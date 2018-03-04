"""
This module holds all error classes which are used in the frontend.
"""
from server.errors import FsimError
from utils.typecheck import ensure_type

from .models import (
    Slave as SlaveModel,
    Script as ScriptModel,
    Filesystem as FilesystemModel,
    Program as ProgramModel,
)


class SlaveOfflineError(FsimError):
    """
    Base class for slave offline Exception's.
    """

    def __init__(self, name, ty, slave, action):
        super().__init__(
            "Could not execute {action} {ty} `{name}` because the client `{slave}` is offline.".
            format(name=name, ty=ty, slave=slave, action=action))

    @staticmethod
    def regex_string():
        return "Could not execute .* .* `.*` because the client `.*` is offline."


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

    @staticmethod
    def regex_string():
        return ".*[Ff]ilesystem.*"


class FilesystemMovedError(FilesystemError):
    """
    If the filesystem is already moved.
    """

    def __init__(self, name, slave):
        super().__init__(
            name, slave,
            "Could not move Filesystem `{}` on client `{}` because it is already moved.".
            format(name, slave))

    @staticmethod
    def regex_string():
        return "Could not move Filesystem `.*` on client `.*` because it is already moved."


class FilesystemNotMovedError(FilesystemError):
    """
    If the filesystem is already moved.
    """

    def __init__(self, name, slave):
        super().__init__(
            name, slave,
            "Could not restore Filesystem `{}` on client `{}` because it is not moved.".
            format(name, slave))

    @staticmethod
    def regex_string():
        return "Could not restore Filesystem `.*` on client `.*` because it is not moved."


class FilesystemDeleteError(FilesystemError):
    """
    If the filesystem is moved then it can not be deleted.
    """

    def __init__(self, name, slave):
        super().__init__(
            name, slave,
            "Can not delete filesystem `{}` on client `{}` because it is still moved. Restore the filesystem and try again.".
            format(name, slave))

    @staticmethod
    def regex_string():
        return "Can not delete filesystem `.*` on client `.*` because it is still moved. Restore the filesystem and try again."


class ProgramError(FsimError):
    """
    Base class for all ProgramError's
    """

    def __init__(self, name, slave, message):
        if message is None:
            message = "An error ocurred in the Program model."

        super().__init__(message)
        self.name = name
        self.slave = slave

    @staticmethod
    def regex_string():
        return ".*[Pp]rogram.*"


class ProgramRunningError(ProgramError):
    """
    If the program is running but an start command was received.
    """

    def __init__(self, name, slave):
        super().__init__(
            name, slave,
            "Can not start the program `{}` on the client `{}` because it is already running".
            format(name, slave))

    @staticmethod
    def regex_string():
        return "Can not start the program `.*` on the client `.*` because it is already running"


class ProgramNotRunningError(ProgramError):
    """
    If the program is not running but an stop command was received.
    """

    def __init__(self, name, slave):
        super().__init__(
            name, slave,
            "Can not stop the program `{}` on the client `{}` because it is not running.".
            format(name, slave))

    @staticmethod
    def regex_string():
        return "Can not stop the program `.*` on the client `.*` because it is not running."


class ObjectNotExistError(FsimError):
    """
    Base class for ObjectNotExistError'S
    """

    def __init__(self, obj_type, identifier):
        super().__init__(
            "The {obj_type} with the id `{identifier}` was not found.".format(
                obj_type=obj_type,
                identifier=identifier,
            ))

    @staticmethod
    def regex_string():
        return "The .* with the id `.*` was not found."


class SlaveNotExistError(ObjectNotExistError):
    """
    This error is wraps the error SlaveMode.DoesNotExist.
    """

    def __init__(self, error, identifier):
        ensure_type("error", error, SlaveModel.DoesNotExist)
        super().__init__("client", identifier)


class ScriptNotExistError(ObjectNotExistError):
    """
    This error is wraps the error ScriptModel.DoesNotExist.
    """

    def __init__(self, error, identifier):
        ensure_type("error", error, ScriptModel.DoesNotExist)
        super().__init__("script", identifier)


class FilesystemNotExistError(ObjectNotExistError):
    """
    This error is wraps the error FilesystemModel.DoesNotExist.
    """

    def __init__(self, error, identifier):
        ensure_type("error", error, FilesystemModel.DoesNotExist)
        super().__init__("filesystem", identifier)


class ProgramNotExistError(ObjectNotExistError):
    """
    This error is wraps the error ProgramModel.DoesNotExist.
    """

    def __init__(self, error, identifier):
        ensure_type("error", error, ProgramModel.DoesNotExist)
        super().__init__("program", identifier)
