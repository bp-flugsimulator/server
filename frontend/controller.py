"""
This module contains functions which modify a Model.
"""

import logging
import os
from shlex import split
from uuid import uuid4

from django.db.models import Q
from django.utils.timezone import now

from wakeonlan import send_magic_packet
from utils import Command
from server.utils import notify, notify_slave

from utils.typecheck import ensure_type

from .models import (
    FILE_BACKUP_ENDING,
    Slave as SlaveModel,
    Script as ScriptModel,
    ScriptGraphFiles as SGF,
    ScriptGraphPrograms as SGP,
    Filesystem as FilesystemModel,
    Program as ProgramModel,
    ProgramStatus as ProgramStatusModel,
)

from .errors import (
    SlaveOfflineError,
    FilesystemMovedError,
    FilesystemNotMovedError,
    FilesystemDeleteError,
    ProgramError,
    ProgramRunningError,
    ProgramNotRunningError,
    LogNotExistError,
)

LOGGER = logging.getLogger("fsim.controller")


def timer_timeout_program(identifier):
    """
    This is callback function which sets the timeout flag for a `ProgramModel`.

    Parameters
    ----------
        identifier: name or int
            An identifier which identifies a `ProgramModel`.
    """
    ProgramStatusModel.objects.filter(program=identifier).update(
        timeouted=True)
    FSIM_CURRENT_SCHEDULER.notify()


def fs_move(fs):
    """
    This functions sends a command to slave to move the given filesystem. If
    any filesystem is at the same place it will be restored and the then `fs`
    will be moved. If the slave is offline an error will be returned.

    Parameters
    ----------
        fs: FilesystemModel
            A valid `FilesystemModel`.

    Raises
    ------
        SlaveOfflineError
        FilesystemMovedError
        TypeError:
            If `fs` is not an `FilesystemModel`
    """
    ensure_type("fs", fs, FilesystemModel)
    slave = fs.slave

    if slave.is_online:
        if fs.is_moved:
            raise FilesystemMovedError(
                str(fs.name),
                str(fs.slave.name),
            )

        if fs.destination_type == 'file':
            lookup_file_name = os.path.basename(fs.source_path)
            lookup_file = fs.destination_path
            (lookup_dir, _) = os.path.split(fs.destination_path)

        elif fs.destination_type == 'dir':
            lookup_file_name = os.path.basename(fs.source_path)
            lookup_file = os.path.join(fs.destination_path, lookup_file_name)
            lookup_dir = fs.destination_path

        query = FilesystemModel.objects.filter(
            ~Q(hash_value__exact='') & ~Q(id=fs.id) & (
                (Q(destination_path=lookup_file) & Q(destination_type='file'))
                | (Q(destination_path=lookup_dir) & Q(destination_type='dir')
                   & (Q(source_path__endswith='/' + lookup_file_name)
                      | Q(source_path__endswith='\\' + lookup_file_name)))))

        if query:
            filesystem_replace = query.get()

            first = Command(
                method="filesystem_restore",
                source_path=filesystem_replace.source_path,
                source_type=filesystem_replace.source_type,
                destination_path=filesystem_replace.destination_path,
                destination_type=filesystem_replace.destination_type,
                backup_ending=FILE_BACKUP_ENDING,
                hash_value=filesystem_replace.hash_value,
            )

            second = Command(
                method="filesystem_move",
                source_path=fs.source_path,
                source_type=fs.source_type,
                destination_path=fs.destination_path,
                destination_type=fs.destination_type,
                backup_ending=FILE_BACKUP_ENDING,
            )

            cmd = Command(
                method="chain_execution",
                commands=[dict(first), dict(second)],
            )

            filesystem_replace.command_uuid = first.uuid
            filesystem_replace.save()

            fs.command_uuid = second.uuid
            fs.save()

        else:
            cmd = Command(
                method="filesystem_move",
                source_path=fs.source_path,
                source_type=fs.source_type,
                destination_path=fs.destination_path,
                destination_type=fs.destination_type,
                backup_ending=FILE_BACKUP_ENDING,
            )

            fs.command_uuid = cmd.uuid
            fs.save()

        # send command to the client
        notify_slave(cmd, slave.id)
    else:
        raise SlaveOfflineError(
            str(fs.name),
            "filesystem",
            str(fs.slave.name),
            "move",
        )


def fs_restore(fs):
    """
    This functions restores a given `fs` by sending a command to the slave to
    restore the original state.  If the slave is offline an error will be
    returned.

    Parameters
    ----------
        fs: FilesystemModel
            A valid `FilesystemModel`.

    Raises
    ------
        SlaveOfflineError
        FilesystemNotMovedError
        TypeError:
            If `fs` is not an `FilesystemModel`
    """
    ensure_type("fs", fs, FilesystemModel)
    slave = fs.slave

    if slave.is_online:
        if not fs.is_moved:
            raise FilesystemNotMovedError(
                str(fs.name),
                str(fs.slave.name),
            )

        cmd = Command(
            method="filesystem_restore",
            source_path=fs.source_path,
            source_type=fs.source_type,
            destination_path=fs.destination_path,
            destination_type=fs.destination_type,
            backup_ending=FILE_BACKUP_ENDING,
            hash_value=fs.hash_value,
        )

        # send command to the client
        notify_slave(cmd, slave.id)

        fs.command_uuid = cmd.uuid
        fs.save()
    else:
        raise SlaveOfflineError(
            str(fs.name),
            "filesystem",
            str(fs.slave.name),
            "restore",
        )


def fs_delete(fs):
    """
    This functions deletes a `fs` only if `fs` is not moved.

    Parameters
    ----------
        fs: FilesystemModel
            A valid `FilesystemModel`.

    Raises
    ------
        FilesystemDeleteError
        TypeError:
            If `fs` is not an `FilesystemModel`
    """
    ensure_type("fs", fs, FilesystemModel)

    if not fs.is_moved:
        fs.delete()
    else:
        raise FilesystemDeleteError(str(fs.name), str(fs.slave.name))


def prog_start(prog):
    """
    This functions starts a `prog` by sending a command to the slave.
    The program can only be started if the program is currently not running.
    If the slave is offline an error will be returned.

    Parameters
    ----------
        prog: ProgramModel
            A valid `ProgramModel`.
    Raises
    ------
        SlaveOfflineError
        ProgramRunningError
        TypeError:
            If `prog` is not an `ProgramModel`
    """
    ensure_type("prog", prog, ProgramModel)

    if prog.slave.is_online:
        if prog.is_running:
            raise ProgramRunningError(str(prog.name), str(prog.slave.name))
        uuid = uuid4().hex

        cmd = Command(
            uuid=uuid,  # for the command
            pid=prog.id,
            own_uuid=uuid,  # for the function that gets executed
            method="execute",
            path=prog.path,
            arguments=[prog.arguments],
        )

        LOGGER.info(
            "Starting program %s on slave %s",
            prog.name,
            prog.slave.name,
        )

        # send command to the client
        notify_slave(cmd, prog.slave.id)

        # tell webinterface that the program has started
        notify({
            'program_status': 'started',
            'pid': prog.id,
        })

        # create status entry
        ProgramStatusModel(
            program=prog, command_uuid=cmd.uuid, start_time=now()).save()

        if prog.start_time > 0:
            LOGGER.debug(
                'started timeout on %s, for %d seconds',
                prog.name,
                prog.start_time,
            )
            LOGGER.debug(type(prog.start_time))
            FSIM_CURRENT_SCHEDULER.spawn(
                prog.start_time,
                timer_timeout_program,
                prog.id,
            )
        elif prog.start_time == 0:
            timer_timeout_program(prog.id)

    else:
        raise SlaveOfflineError(
            str(prog.name),
            "program",
            str(prog.slave.name),
            "start",
        )


def prog_stop(prog):
    """
    This function stops a `prog` by sending a command to the slave.
    The program can only be stoped if the program is currently running. If the
    slave is offline an error will be returned.

    Parameters
    ----------
        prog: ProgramModel
            A valid `ProgramModel`.

    Exception
    -------
        SlaveOfflineError
        ProgramNotRunningError
        TypeError:
            If `prog` is not an `ProgramModel`
    """
    ensure_type("prog", prog, ProgramModel)

    if prog.slave.is_online:
        if not prog.is_running:
            raise ProgramNotRunningError(str(prog.name), str(prog.slave.name))

        LOGGER.info(
            "Stoping program %s on slave %s",
            prog.name,
            prog.slave.name,
        )

        notify_slave(
            Command(
                method="execute",
                uuid=prog.programstatus.command_uuid,
            ),
            prog.slave.id,
        )
    else:
        raise SlaveOfflineError(
            str(prog.name),
            "program",
            str(prog.slave.name),
            "stop",
        )


def slave_shutdown(slave):
    """
    This functions shutsdown a `slave` by a command to the slave.

    Parameters
    ----------
        slave: SlaveModel
            A valid `SlaveModel`.

    Raises
    ------
        TypeError:
            If `slave` is not an `SlaveModel`
    """
    if slave.is_online:
        notify_slave(Command(method="shutdown"), slave.id)
        notify({"message": "Send shutdown Command to {}".format(slave.name)})
    else:
        raise SlaveOfflineError('', '', 'shutdown', slave.name)


def slave_wake_on_lan(slave):
    """
    This functions starts a `slave` by sending a magic (Wake-On-Lan
    package) to the `slave`.

    Parameters
    ----------
        slave: SlaveModel
            A valid `SlaveModel`.

    Raises
    ------
        TypeError:
            If `slave` is not an `SlaveModel`
    """
    ensure_type("slave", slave, SlaveModel)
    send_magic_packet(slave.mac_address)

    notify({"message": "Send start command to client `{}`".format(slave.name)})


def prog_log_get(program):
    """
    This function is asking for a log for a `program` by sending a command to
    the slave. If the slave is offline an error will be returned.

    Parameters
    ----------
        program: ProgramModel
            A valid `ProgramModel`.

    Raises
    ------
        SlaveOfflineError
        LogNotExistError
        TypeError:
            If `program` is not an `ProgramModel`
    """
    ensure_type("program", program, ProgramModel)

    LOGGER.info(
        "Requesting log for program %s on slave %s",
        program.name,
        program.slave.name,
    )

    if not program.slave.is_online:
        raise SlaveOfflineError('', '', 'get_log', program.slave.name)

    if not (program.is_executed or program.is_running):
        raise LogNotExistError(program.id)

    notify_slave(
        Command(
            method="get_log",
            target_uuid=program.programstatus.command_uuid,
        ),
        program.slave.id,
    )


def prog_log_enable(program):
    """
    This function enables the log transfer for a `ProgramModel` by sending a
    command to the slave. Not all programs support the log function. If the
    slave is offline an error will be returned.

    Parameters
    ----------
        program: ProgramModel
            A valid `ProgramModel`.

    Raises
    ------
        SlaveOfflineError
        LogNotExistError
        TypeError:
            If `program` is not an `ProgramModel`
    """
    ensure_type("program", program, ProgramModel)

    LOGGER.info(
        "Enabling logging for program %s on slave %s",
        program.name,
        program.slave.name,
    )

    if not program.slave.is_online:
        raise SlaveOfflineError('', '', 'log_enable', program.slave.name)

    if not (program.is_executed or program.is_running):
        raise LogNotExistError(program.id)

    notify_slave(
        Command(
            method="enable_logging",
            target_uuid=program.programstatus.command_uuid,
        ),
        program.slave.id,
    )


def prog_log_disable(program):
    """
    This function disables the log transfer for a `ProgramModel` by sending a
    command to the slave. If the slave is offline an error will be returned.

    Parameters
    ----------
        program: ProgramModel
            A valid `ProgramModel`.

    Raises
    ------
        SlaveOfflineError
        TypeError:
            If `program` is not an `ProgramModel`
    """
    ensure_type("program", program, ProgramModel)

    LOGGER.info(
        "Disabling logging for program %s on slave %s",
        program.name,
        program.slave.name,
    )

    if not program.slave.is_online:
        raise SlaveOfflineError('', '', 'log_disable', program.slave.name)

    notify_slave(
        Command(
            method="disable_logging",
            target_uuid=program.programstatus.command_uuid,
        ),
        program.slave.id,
    )


def script_deep_copy(script):
    """
    This function creates a copy of a `ScriptModel` with all `ScriptGraphFiles`
    and `ScriptGraphPrograms`. The result `ScriptModle` has the same name but
    with an suffix '_copy'. If the `ScriptModel` with the suffix already exists
    then a number is appended to the name.

    Parameters
    ----------
        slave: ScriptModel
            A valid `ScriptModel`.

    Returns
    -------
        copy: ScriptModel
            The copy of the `script` with a new name.

    Raises
    ------
        TypeError:
            If `script` is not an `ScriptModel`
    """
    ensure_type("script", script, ScriptModel)
    i = 0
    copy = None

    while not copy:
        if i is 0:
            name = script.name + '_copy'
        else:
            name = script.name + '_copy_' + str(i)

        if ScriptModel.objects.filter(name=name).exists():
            i = i + 1
        else:
            copy = ScriptModel(name=name)

    copy.save()
    for file_entry in SGF.objects.filter(script_id=script.id):
        SGF(script=copy,
            index=file_entry.index,
            filesystem=file_entry.filesystem).save()

    for program_entry in SGP.objects.filter(script_id=script.id):
        SGP(script=copy,
            index=program_entry.index,
            program=program_entry.program).save()

    return copy
