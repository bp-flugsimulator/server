"""
This module holds all error classes which are used in the frontend.
"""
from server.errors import FsimError
from utils.typecheck import ensure_type

from frontend import models

class SlaveOfflineError(FsimError):
    """
    This class gets raised if an `SlaveModel` is not online, but is expected to
    be online to execute the wanted action.
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
    This class is the base class for all error which are only related to the
    `FileModel`.
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
    This class is raised if move command on the `FilesystemModel` failed
    because the `FilesystemModel` already moved.
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
    This class is raised if restore command on the `FilesystemModel` failed
    because the `FilesystemModel` is not moved.
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
    This class is raised if delete command on the `FilesystemModel` failed
    because the `FilesystemModel` is still moved.
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
    This class is the base class for all error which are only related to the
    `ProgramModel`.
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
    This class is raised if a start command on the `ProgramModel` failed because
    the `ProgramModel` is already running.
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
    This class is raised if a stop command on the `ProgramModel` failed because
    the `ProgramModel` was not started yet.
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
    This class is the base class for all error which are only related to the
    Django error where the object could not be found in the database.
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
    This error is wraps the error `SlaveMode.DoesNotExist`.
    """

    def __init__(self, error, identifier):
        ensure_type("error", error, models.Slave.DoesNotExist)
        super().__init__("client", identifier)


class ScriptNotExistError(ObjectNotExistError):
    """
    This error is wraps the error `ScriptModel.DoesNotExist`.
    """

    def __init__(self, error, identifier):
        ensure_type("error", error, models.Script.DoesNotExist)
        super().__init__("script", identifier)


class FilesystemNotExistError(ObjectNotExistError):
    """
    This error is wraps the error `FilesystemModel.DoesNotExist`.
    """

    def __init__(self, error, identifier):
        ensure_type("error", error, models.Filesystem.DoesNotExist)
        super().__init__("filesystem", identifier)


class ProgramNotExistError(ObjectNotExistError):
    """
    This error is wraps the error `ProgramModel.DoesNotExist`.
    """

    def __init__(self, error, identifier):
        ensure_type("error", error, models.Program.DoesNotExist)
        super().__init__("program", identifier)


class LogNotExistError(ObjectNotExistError):
    """
    This class is raised if a log from a `ProgramModel` was requested but not
    that `ProgramModel` does not have one.
    """

    def __init__(self, identifier):
        super().__init__("log from program", identifier)


class QueryError(FsimError):
    """
    This class is the base class for all error which are only related to the
    errors where the query paramater are not valid.
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
    This class is raised if query paramaters are set at the same time, but it
    is not suppose to.
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
    This class is the base class for all error which are only related to the
    `ScriptModel`.
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
    This class is raised if a `ScriptModel` was tried to start, but a `Script`
    is already running.
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
    This class is raised if an query parameter has not the format of the given
    values.
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
    This class is raised if an query got an value which could not be
    transformed properly.
    """

    def __init__(self, given, expected):
        super().__init__(
            "Expected something that can be transformed into `{}` from `{}`.".
            format(
                expected,
                given,
            ), )

    @staticmethod
    def regex_string():
        return "Expected something that can be transformed into `.*` from `.*`."


class PositiveNumberError(FsimError):
    """
    This class is raised if an value was not zero or positive.
    """

    def __init__(self, given, name):
        super().__init__("Expected zero or positive for {} (given: {})".format(
            name, given))

    @staticmethod
    def regex_string():
        return "Expected zero or positive for .* \(given: .*\)"

class IdentifierError(FsimError):
    """
    This class is raised if an identifier could not be used as intended.
    """
    def __init__(self, name, ty, given):
        super().__init__(
            "The given type `{}` for `{}` is not compatible. (given value: `{}`)".format(
            ty, name, given))

    @staticmethod
    def regex_string():
        return "The given type `.*` for `.*` is not compatible. \(given value: `.*`\)"

