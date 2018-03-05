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


class LogNotExistError(ObjectNotExistError):
    """
    This error is thrown if a log of a program gets requested that
    cannot have a log.
    """

    def __init__(self, identifier):
        super().__init__("log from program", identifier)


class QueryError(FsimError):
    """
    Base Class for Query errors
    """

    def __init__(self, message):
        if message:
            super().__init__(message)
        else:
            super().__init__("There was an error while querying.")

    @staticmethod
    def regex_string():
        return "[Qq]uery"


class SimultaneousQueryError(QueryError):
    """
    This error is raised, if two queries with different types get requested at the same time
    """

    def __init__(self, param1, param2):
        super().__init__(
            "Can not query for {} and {} at the same time.".format(
                param1, param2))

    @staticmethod
    def regex_string():
        return "Can not query for .* and .* at the same time."


class ScriptError(FsimError):
    """
    Base class for all ScriptError's
    """

    def __init__(self, script, message):
        if message is None:
            message = "An error ocurred in the Script model."

        super().__init__(message)
        self.script = script

    @staticmethod
    def regex_string():
        return "[Ss]cript"


class ScriptRunningError(ScriptError):
    """
    Script is running while trying to start it again.
    """

    def __init__(self, script):
        super().__init__(
            script,
            "The script `{}` is already running and can not be started again.".
            format(script))

    @staticmethod
    def regex_string():
        return "The script `.*` is already running and can not be started again."


class QueryParameterError(QueryError):
    """
    The given parameter for the query is not supported.
    """

    def __init__(self, given_type, expected_types):
        super().__init__("Expected one of `{}` but got `{}` instead.".format(
            given_type,
            ' or'.join(expected_types),
        ), )

    @staticmethod
    def regex_string():
        return "Expected one of `.*` but got `.*` instead."


class QueryTypeError(QueryError):
    """
    The given parameter has not the matching type.
    """

    def __init__(self, given, expected):
        super().__init__(
            "Expected something that can be transformet into `{}` from `{}`.".
            format(
                expected,
                given,
            ), )

    @staticmethod
    def regex_string():
        return "Expected something that can be transformet into `.*` from `.*`."
