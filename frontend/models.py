"""
This module contains all database models from the `frontend` application.
"""

import logging
from shlex import split
from uuid import uuid4

from utils.typecheck import ensure_type

from django.db.models import (
    Model,
    CharField,
    GenericIPAddressField,
    ForeignKey,
    CASCADE,
    IntegerField,
    BooleanField,
    OneToOneField,
    TextField,
    Count,
    Q,
)

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from wakeonlan import send_magic_packet
from utils import Command
from server.utils import notify

from .errors import IdentifierError

LOGGER = logging.getLogger("fsim.models")
FILE_BACKUP_ENDING = "_BACK"


def validate_mac_address(mac_addr):
    """
    Validates a given MAC address.

    This functions checks if a given string is a valid
    MAC address.

    Parameters
    ----------
        mac_addr: str
            MAC address

    Exception
    ---------
        ValidationError:
            If `mac_addr` is not a valid MAC address.
    """

    def ishex(char):
        """
        Checks if a given character is a hex character.

        Parameters
        ----------
            char: str
                A single character
        """
        return (char <= 'F' and char >= 'A') or (char <= 'f' and char >= 'a')

    parts = mac_addr.split(":")
    if len(parts) == 6:
        for part in parts:
            for char in part:
                if (not ishex(char) and not char.isdigit()) or len(part) != 2:
                    raise ValidationError(
                        _('Enter a valid MAC Address.'),
                        code='invalid_mac_sym',
                    )
    else:
        raise ValidationError(
            _('Enter a valid MAC Address.'),
            code='invalid_mac_few',
        )


def validate_argument_list(args):
    """
    Validates a list of command line arguments if it is parseable.

    Parameters
    ----------
        args: str
            A string which contains command line arguments.

    Exception
    ---------
        ValidationError:
            If the given `args` are not parseable by `shlex`.
    """
    try:
        split(args)
    except ValueError:
        raise ValidationError(_('Enter a valid argument list.'), )


class Slave(Model):
    """
    Reprents a slave which runs the counter part of this software. The slave is
    located in a network.

    Attributes
    ----------
        name: CharField
            The unique name of the `Slave`.
        ip_address: GenericIPAddressField
            The IP address which is used to address packages to the slave.
        mac_address: CharField(validators=[validate_mac_address])
            The MAC address of the slave.

        command_uuid:
            The UUID which is related to the RPC command.
        online:
            If the client has connected to the server

    """
    #persistent fields
    name = CharField(unique=True, max_length=200)
    ip_address = GenericIPAddressField(unique=True)
    mac_address = CharField(
        unique=True,
        max_length=17,
        validators=[validate_mac_address],
    )

    #non persistent fields
    command_uuid = CharField(blank=True, null=True, max_length=32, unique=True)
    online = BooleanField(unique=False, default=False)

    def reset(self):
        """
        Resets non persistent fields to their default value.
        """
        self.command_uuid = None
        self.online = False

        self.save()

    @property
    def is_online(self):
        """
        Checks if the slave is online.

        Returns
        -------
            bool:
                If the slave is online.
        """
        return self.online

    @property
    def has_error(self):
        """
        Checks if the slave has an error value stored.

        Returns
        -------
            bool:
                If the slave has an error value stored.
        """
        for prog in self.program_set.all():
            if prog.is_error:
                return True

        for filesystem in self.filesystem_set.all():
            if filesystem.is_error:
                return True

        return False

    @property
    def has_running(self):
        """
        Checks if the slave has running programs.

        Returns
        -------
            bool:
                If the slave has running programs.
        """
        return self.program_set.filter(programstatus__running=True).exists()

    @staticmethod
    def from_identifier(identifier, is_string):
        """
        Returns an slave based on the given `identifier` which can be an index or
        a name.

        Parameters
        ----------
            identifier: str
                Which is a `name` or `index` form the `Slave` model.
            is_string: bool
                If the `identifier` should be interpreted as a `name` or `index`.

        Returns
        -------
            Slave:
                If the type was correct and the slave exist.

        Raises
        ------
            Slave.DoesNotExist:
                If no slave with the given `identifier` exist.
            TypeError:
                If `identifier` and `is_string` have not the correct type.
            IdentifierError:
                If `is_string` is False and the `identifier` can not be
                transformed into an int.
        """
        ensure_type("identifier", identifier, str)
        ensure_type("is_string", is_string, bool)

        if is_string:
            return Slave.objects.get(name=identifier)
        else:
            try:
                return Slave.objects.get(id=int(identifier))
            except ValueError:
                raise IdentifierError("slave", "int", identifier)

    @staticmethod
    def with_programs():
        """
        Returns all `Slave`s witch have at least one program.

        Returns
        -------
            list of str:
                The list contains the name of every `Slave` which fulfil the
                condition.
        """
        return Slave.objects.all().annotate(prog_count=Count(
            'program__pk')).filter(prog_count__gt=0).values_list(
                'name',
                flat=True,
            )

    @staticmethod
    def with_filesystems():
        """
        Returns all `Slave`s witch have at least one filesystem.

        Returns
        -------
            list of str:
                The list contains the name of every `Slave` which fulfil the
                condition.
        """
        return Slave.objects.all().annotate(filesystem_count=Count(
            'filesystem__pk')).filter(filesystem_count__gt=0).values_list(
                'name',
                flat=True,
            )


class Program(Model):
    """
    Represents a program which is located on a slave and which can be executed.

    Attributes
    ----------
        name: CharField
            The name of the `Program`, which is unique to every `Slave`.
        path: TextField
            A full path to the `Program` on the same `Slave`.
        arguments: TextField
            Arguments for the executable `Program`.
        slave: ForeignKey
            The `Slave` on which this `Program` is located.
        start_time: IntegerField
            The amount of time this `Program` needs to start.
    """
    name = CharField(unique=False, max_length=1000)
    path = TextField(unique=False)
    arguments = TextField(
        unique=False,
        blank=True,
        validators=[validate_argument_list],
    )
    slave = ForeignKey(Slave, on_delete=CASCADE)
    start_time = IntegerField(default=-1)

    class Meta:
        """
        Meta class
        """
        unique_together = (('name', 'slave'), )

    def __str__(self):
        return str(self.name)

    @property
    def data_state(self):
        """
        Returns the current state of this `Filesystem` as a string.

        Returns
        -------
            str:
                One of "running", "error", "success" or "unknown"
        """
        if self.is_running:
            return "running"
        elif self.is_error:
            return "error"
        elif self.is_executed:
            return "success"
        else:
            return "unknown"

    @property
    def is_timeouted(self):
        """
        Checks if the `Program.start_time` is elapsed.

        Returns
        -------
            bool:
                If the specified amount of time is elapsed.
        """
        try:
            return self.programstatus.timeouted
        except ProgramStatus.DoesNotExist:
            return False

    @property
    def is_running(self):
        """
        Checks if this `Program` is running.

        Returns
        -------
            bool:
                If this `Program` is running.
        """
        try:
            return self.programstatus.running
        except ProgramStatus.DoesNotExist:
            return False

    @property
    def is_executed(self):
        """
        Checks if this `Program` was running in the past.

        Returns
        -------
            bool:
                If this `Program` was running.
        """
        try:
            return not self.is_running and self.programstatus.code != ''
        except ProgramStatus.DoesNotExist:
            return False

    @property
    def is_error(self):
        """
        Checks if this `Program` had an error while running.

        Returns
        -------
            bool:
                If this `Program` had an error.
        """
        # NOTICE: `Program.is_executed` covers the case
        # `ProgramStatus.DoesNotExist`.
        return self.is_executed and self.programstatus.code != '0'

    @property
    def is_successful(self):
        """
        Checks if this `Program` had no errors while running.

        Returns
        -------
            bool:
                If this `Program` had no error.
        """
        # NOTICE: `Program.is_executed` covers the case
        # `ProgramStatus.DoesNotExist`.
        return self.is_executed and self.programstatus.code == '0'


class Filesystem(Model):
    """
    Represents a file or directory on a `Slave` which can be moved to another
    specified location on the same `Slave`.

    Attributes
    ----------
        name: CharField
            The unique name for this `Filesystem`
        slave: ForeignKey
            The `Slave` on which this `Filesystem` is on.
        source_path: TextField
            The path to the existing file or directory on the `Slave`.
        source_type: CharField
            Specifies if the source_path is directory or a file.
        destination_path: TextField
            The path where the `source_path` object should be moved to.
        destination_type: CharField
            Specifies if the `source_path` should be replaced with or, if the
            `destination_path` is directory, replace with.
        hash_value: CharField
            This field is set if this `Filesystem` is moved. The content is
            equal to the hash value of the corresponding file or directory
            (`source_path`).

        command_uuid: CharField
            An UUID which identifies the send command.
        error_code: str
            The error code which is raised by the slave.
    """

    CHOICES_SET_SOURCE = [
        ('file', 'File'),
        ('dir', 'Directory'),
    ]
    CHOICES_SET_DESTINATION = [
        ('file', 'Replace with'),
        ('dir', 'Insert into'),
    ]

    # persistant fields
    name = CharField(unique=False, max_length=200)
    slave = ForeignKey(Slave, on_delete=CASCADE)
    source_path = TextField(unique=False)
    source_type = CharField(
        max_length=4, choices=CHOICES_SET_SOURCE, default='file')
    destination_path = TextField(unique=False)
    destination_type = CharField(
        max_length=4,
        choices=CHOICES_SET_DESTINATION,
        default='file',
    )
    hash_value = CharField(
        unique=False,
        max_length=32,
        blank=True,
        default="",
    )

    # state fields
    command_uuid = CharField(
        max_length=32,
        unique=True,
        blank=True,
        null=True,
    )
    error_code = CharField(blank=True, default="", max_length=1000)

    class Meta:
        """
        Meta class
        """
        unique_together = (
            ('name', 'slave'),
            (
                'source_path',
                'destination_path',
                'slave',
                'source_type',
                'destination_type',
            ),
        )

    def reset(self):
        """
        Resets non persistent fields to their default value.
        """
        self.command_uuid = None
        self.error_code = ""

        self.save()

    def __str__(self):
        return self.name

    @property
    def is_moved(self):
        """
        Checks if this `Filesystem` `source_path` is moved to
        `destination_path`.

        Returns
        -------
            bool:
                If this `Filesystem` is moved.
        """
        return self.hash_value is not None and self.hash_value != ""

    @property
    def is_error(self):
        """
        Checks if this `Filesystem` had an error while the move or restore
        operation.

        Returns
        -------
            bool:
                If this `Filesystem` had an error.
        """
        return self.error_code != ''

    @property
    def data_state(self):
        """
        Returns the current state of this `Filesystem` as a string.

        Returns
        -------
            str:
                One of "error", "moved" or "restored".
         """
        if self.is_error:
            return "error"
        elif self.is_moved:
            return "moved"
        else:
            return "restored"


class Script(Model):
    """
    Represents a `Script` which has different `Program`s and `Filesystem`s. A
    `Script` can also be executed.

    Attributes
    ----------
        name: CharField
            The unqiue name for this `Script`.
        last_ran: BooleanField
            If this `Script` was the last one which was executed successful.

        is_initialized: BooleanField
            If this `Scheduler` started this `Script`.
        is_running: BooleanField
            If this `Script` is currently running, by the `Scheduler`.
        error_code: CharField
            The message which is set if an error occurred.
        current_index: IntegerField
            If the `Script` is running, then this field contains the current
            index/stage.
    """
    #persistent fields
    name = CharField(unique=True, blank=False, max_length=200)
    last_ran = BooleanField(default=False, blank=True)

    #non persistent fields
    is_initialized = BooleanField(default=False, blank=True)
    is_running = BooleanField(default=False, blank=True)
    error_code = CharField(default="", max_length=1000, blank=True)
    current_index = IntegerField(default=-1, blank=True)

    def reset(self):
        """
        Resets non persistent fields to their default value.
        """
        self.is_initialized = False
        self.is_running = False
        self.error_code = ""
        self.current_index = -1

        self.save()

    def __str__(self):
        return self.name

    @property
    def indexes(self):
        """
        Returns all indexes which are used in this `Script`.

        Returns
        -------
            list of int:
                Which contains all indexes which are used by this `Script`.
                Every index only occurs once in this list (no duplications).
        """
        query_program = ScriptGraphPrograms.objects.filter(
            script=self).values_list(
                "index", flat=True).annotate(Count("id")).order_by("index")

        query_filesystems = ScriptGraphFiles.objects.filter(
            script=self).values_list(
                "index", flat=True).annotate(Count("id")).order_by("index")

        query = set(query_filesystems).union(set(query_program))

        return list(query)

    @property
    def has_error(self):
        """
        Checks if this `Script` had an error.

        Returns
        -------
            bool:
                If this `Script` had an error.
        """
        return self.error_code != ''

    @staticmethod
    def set_last_started(script):
        """
        Sets the `Script.last_ran` flag to True for this `Script`, while
        setting the flag to False for all other `Scripts`.
        """
        Script.objects.all().update(last_ran=False)
        Script.objects.filter(id=script).update(last_ran=True)

    @staticmethod
    def check_online(script):
        """
        Checks if all relevant `Slave`s are online.

        Arguments
        ---------
            script: Script
                A valid `Script`

        Returns
        -------
            bool:
                If all relevant `Slave`s are online.
        """

        return not Program.objects.filter(
            scriptgraphprograms__script=script,
            slave__online=False,
        ).exists()

    @staticmethod
    def get_involved_slaves(script):
        """
        Gets all `Slave`s which are have `Program`s or `Filesystem`s, that are
        used in this `Script`.

        Arguments
        ---------
            script: Script
                A valid `Script`

        Returns
        -------
            list of `Slave`s:
                With all `Slave`s that are used in this `Script`.
        """
        return Program.objects.filter(
            scriptgraphprograms__script=script).annotate(
                dcount=Count('slave')).values_list(
                    'slave',
                    flat=True,
                )


class ScriptGraphPrograms(Model):
    """
    Represents a `Program` which is involved in `Script`.

    Attributes
    -------
        script: ForeignKey
            The `Script` which this entry belongs to.
        index: IntegerField
            The order in which each entry is executed. (ordered)
        program: ForeignKey
            The `Program` which is executed.
    """
    script = ForeignKey(Script, on_delete=CASCADE)
    index = IntegerField(null=False)
    program = ForeignKey(Program, on_delete=CASCADE)

    class Meta:
        unique_together = (('script', 'index', 'program'), )


class ScriptGraphFiles(Model):
    """
    Represents a dependency graph for  in a script file.

    Attributes
    -------
        script: ForeignKey
            The `Script` which this entry belongs to.
        index: IntegerField
            The order in which each entry is executed. (ordered)
        filesystem: ForeignKey
            The `Filesytem` which is moved.
    """
    script = ForeignKey(Script, on_delete=CASCADE)
    index = IntegerField(null=False)
    filesystem = ForeignKey(Filesystem, on_delete=CASCADE)

    class Meta:
        unique_together = (('script', 'index', 'filesystem'), )


class ProgramStatus(Model):
    """
    Represents the current status of an `Program`.

    Attributes
    -----------
        program: ForeignKey
            The related `Program`.
        code: CharField
            The return code of an execution of the related `Program`.
        command_uuid: CharField
            An UUID which identifies the send command.
        running: BooleanField
            Indicator if the `Program` is running.
        timeouted: BooleanField
            Indicator if the `Program` elapsed the amount of time it needs to
            execute.
    """
    program = OneToOneField(
        Program,
        on_delete=CASCADE,
        primary_key=True,
    )
    code = CharField(max_length=200, unique=False, blank=True)
    command_uuid = CharField(max_length=32, unique=True)
    running = BooleanField(unique=False, default=True)
    timeouted = BooleanField(unique=False, default=False)
