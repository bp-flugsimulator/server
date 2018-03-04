"""
Controller
"""

import logging
import os
from shlex import split
from uuid import uuid4

from django.core.cache import cache
from django.db.models import (
    Count,
    Q,
)

from channels import Group
from wakeonlan import send_magic_packet
from utils import Command
from server.utils import notify

from utils.typecheck import ensure_type

from .models import (
    FILE_BACKUP_ENDING,
    Slave as SlaveModel,
    Filesystem as FilesystemModel,
    Program as ProgramModel,
    ProgramStatus as ProgramStatusModel,
)

from .errors import (
    FilesystemError,
    SlaveOfflineError,
    FilesystemMovedError,
    FilesystemNotMovedError,
    FilesystemDeleteError,
    ProgramError,
    ProgramRunningError,
    ProgramNotRunningError,
)

LOGGER = logging.getLogger("fsim.controller")


def timer_timeout_program(identifier):
    """
    Sets the timeout flag for a program.

    Arguments
    ---------
        id: Program id
    """
    ProgramStatusModel.objects.filter(program=identifier).update(
        timeouted=True)
    FSIM_CURRENT_SCHEDULER.notify()


def fs_move(fs):
    """
    Moves the file on the slave.

    Exception
    -------
        SlaveOfflineError
        FilesystemMovedError
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
        Group('client_' + str(slave.id)).send({'text': cmd.to_json()})
    else:
        raise SlaveOfflineError(
            str(fs.name),
            "filesystem",
            str(fs.slave.name),
            "move",
        )


def fs_restore(fs):
    """
    Restores the file on the slave.

    Exception
    -------
        SlaveOfflineError
        FilesystemNotMovedError
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
        Group('client_' + str(slave.id)).send({'text': cmd.to_json()})

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
    Deletes the entry in the database.

    Exception
    -------
        FilesystemDeleteError
    """
    ensure_type("fs", fs, FilesystemModel)

    if not fs.is_moved:
        fs.delete()
    else:
        raise FilesystemDeleteError(str(fs.name), str(fs.slave.name))


def prog_start(prog):
    """
    Starts the program on the slave.

    Exception
    -------
        SlaveOfflineError
        ProgramRunningError
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
            arguments=split(prog.arguments),
        )

        LOGGER.info(
            "Starting program %s on slave %s",
            prog.name,
            prog.slave.name,
        )

        # send command to the client
        Group('client_' + str(prog.slave.id)).send({'text': cmd.to_json()})

        # tell webinterface that the program has started
        notify({
            'program_status': 'started',
            'pid': prog.id,
        })

        # create status entry
        ProgramStatusModel(program=prog, command_uuid=cmd.uuid).save()

        if prog.start_time >= 0:
            LOGGER.debug(
                'started timeout on %s, for %d seconds',
                prog.name,
                prog.start_time,
            )

            FSIM_CURRENT_SCHEDULER.spawn(
                prog.start_time,
                timer_timeout_program,
                prog.id,
            )

    else:
        raise SlaveOfflineError(
            str(prog.name),
            "program",
            str(prog.slave.name),
            "start",
        )


def prog_stop(prog):
    """
    Stops the program on the slave.

    Exception
    -------
        SlaveOfflineError
        ProgramNotRunningError
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

        Group('client_' + str(prog.slave.id)).send({
            'text':
            Command(
                method="execute",
                uuid=prog.programstatus.command_uuid,
            ).to_json()
        })
    else:
        raise SlaveOfflineError(
            str(prog.name),
            "program",
            str(prog.slave.name),
            "stop",
        )


def slave_wake_on_lan(slave):
    """
    Sends wake on lan package to the slave.
    """
    ensure_type("slave", slave, SlaveModel)
    send_magic_packet(slave.mac_address)


def log_get(prog):
    """
    Requests a log of the program on the slave.

        Returns
    -------
        boolean which indicates if the Request was possible.
    """
    ensure_type("prog", prog, ProgramModel)

    LOGGER.info(
        "Requesting log for program %s on slave %s",
        prog.name,
        prog.slave.name,
    )
    if prog.slave.is_online:
        Group('client_' + str(prog.slave.id)).send({
            'text':
            Command(
                method="get_log",
                target_uuid=prog.programstatus.command_uuid).to_json()
        })
        return True
    else:
        return False


def log_enable(prog):
    ensure_type("prog", prog, ProgramModel)

    LOGGER.info(
        "Enabling logging for program %s on slave %s",
        prog.name,
        prog.slave.name,
    )

    if prog.slave.is_online:
        Group('client_' + str(prog.slave.id)).send({
            'text':
            Command(
                method="enable_logging",
                target_uuid=prog.programstatus.command_uuid,
            ).to_json()
        })
        return True
    else:
        return False


def log_disable(prog):
    ensure_type("prog", prog, ProgramModel)

    LOGGER.info(
        "Disabling logging for program %s on slave %s",
        prog.name,
        prog.slave.name,
    )

    if prog.slave.is_online:
        Group('client_' + str(prog.slave.id)).send({
            'text':
            Command(
                method="disable_logging",
                target_uuid=prog.programstatus.command_uuid,
            ).to_json()
        })
        return True
    else:
        return False
