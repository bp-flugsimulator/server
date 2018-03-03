"""
This module contains all databasemodels from the frontend application.
"""

import logging
import os

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
from channels import Group
from wakeonlan import send_magic_packet
from utils import Command
from server.utils import notify

LOGGER = logging.getLogger("fsim.models")
FILE_BACKUP_ENDING = "_BACK"


def validate_mac_address(mac_addr):
    """
    Validates a given MAC address.

    This functions checks if a given string is a valid
    MAC address.

    Parameters
    ----------
    mac_addr : str
        MAC address

    Returns
    -------
    nothing

    Exception
    ---------
    Raises an ValidationError if the given string is not
    a valid MAC address.
    """

    def ishex(char):
        """
        checks if char is a hexvalue
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
    Validates that given argument list is parsable by shlex.

    Parameters
    ----------
    args: str
        argument list

    Returns
    -------
    nothing

    Exception
    ---------
    Raises an ValidationError if the given argument list is
    not parsable by shlex.
    """
    try:
        split(args)
    except ValueError:
        raise ValidationError(_('Enter a valid argument list.'), )


class Slave(Model):
    """
    Represents a slave which is node in the network. This is stored in a
    database.

    Members
    -------
    name: str The name of the slave
    ip_address: GenericIPAddressField The IP address of the slave.
    mac_address: str The MAC address of the slave.
    command_uuid: The UUID which is related to the RPC command.
    online: If the client has connected to the server

    """
    name = CharField(unique=True, max_length=200)
    ip_address = GenericIPAddressField(unique=True)
    mac_address = CharField(
        unique=True,
        max_length=17,
        validators=[validate_mac_address],
    )
    command_uuid = CharField(blank=True, null=True, max_length=32, unique=True)
    online = BooleanField(unique=False, default=False)

    @property
    def is_online(self):
        """
        Returns true of the current slave has connected to the master.
        """
        return self.online

    @property
    def has_error(self):
        """
        Returns true if any program or filesystem is in an error state.
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
        Returns true if any program or filesystem is in an error state.
        """
        return self.program_set.filter(programstatus__running=True).exists()


class Program(Model):
    """
    Represents a program on a slave This is stored in a database.

    Members
    -------
    name: str The name of the program (has to be unique for every slave)

    path: str The path to the binary filesystem that will be executed

    arguments: str The arguments which will be passed to the executable on
        execution

    slave: Slave The slave on which the command will be executed

    start_time: int The amount of time a program needs to start.
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
        unique_together = (('name', 'slave'), )

    @property
    def is_timeouted(self):
        """
        Returns true if the time which the program takes to start is over.
        """
        try:
            return self.programstatus.timeouted
        except ProgramStatus.DoesNotExist:
            return False

    @property
    def is_running(self):
        """
        Returns true if program is currently running.
        """
        try:
            return self.programstatus.running
        except ProgramStatus.DoesNotExist:
            return False

    @property
    def is_executed(self):
        """
        Returns true if the program exited.
        """
        try:
            return not self.is_running and self.programstatus.code != ''
        except ProgramStatus.DoesNotExist:
            return False

    @property
    def is_error(self):
        """
        Returns true if the current program was executed not successful, which
        means the error code was 0.
        """
        # NOTICE: no try and catch needed because self.is_executed is False
        # if ProgramStatus.DoesNotExist is thrown, thus the whole expression
        # is false
        return self.is_executed and self.programstatus.code != '0'

    @property
    def is_successful(self):
        """
        Returns true if the current program was executed successful.
        """
        # NOTICE: no try and catch needed because self.is_executed is False
        # if ProgramStatus.DoesNotExist is thrown, thus the whole expression
        # is false
        return self.is_executed and self.programstatus.code == '0'


class Filesystem(Model):
    """
    Represents a filesystem on a slave This is stored in a database.

    Members
    -------
    name: str The name of the filesystem (has to be unique for every slave)

    source_path: str
        The path to the source of the filesystem

    destination_path: str
        The path there the filesystem should be used in the filesystem system

    error_code: str
        The error code which is raised by the slave.

    slave: Slave The slave on which the filesystem belongs to
    """

    CHOICES_SET_SOURCE = [
        ('file', 'Source is a file'),
        ('dir', 'Source is a directory'),
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

    def __str__(self):
        return self.name

    @property
    def is_moved(self):
        """
        Returns true if filesystem is moved.
        """
        return self.hash_value is not None and self.hash_value != ""

    @property
    def is_error(self):
        return self.error_code != ''

    @property
    def data_state(self):
        """
        Returns a string which represents the data-state attribute in the html template.
        """
        # {% if filesystem.is_error %}error{% elif filesystem.is_moved %}moved{% else %}restored{% endif %}
        if self.is_error:
            return "error"
        elif self.is_moved:
            return "moved"
        else:
            return "restored"


class Script(Model):
    """
    Represents a script file in a json format.

    Members
    -------
    name: str
        The name of the script (has to be unique for every slave)
    """
    name = CharField(unique=True, max_length=200)
    last_ran = BooleanField(default=False)
    is_initialized = BooleanField(default=False)
    is_running = BooleanField(default=False)
    error_code = CharField(default="", max_length=1000)
    current_index = IntegerField(default=-1)

    def __str__(self):
        return self.name

    @property
    def indexes(self):
        """
        Returns a query which contains the index and 'id__count' which holds
        the amount of index for one script.

        Returns
        -------
            array of maps where 'index' and 'id__count' is in.
        """
        query = ScriptGraphPrograms.objects.filter(
            script=self).values("index").annotate(
                Count("id")).order_by("index")

        return query

    @property
    def has_error(self):
        """
        Returns true if the error code is set.

        Returns
        -------
            bool
        """
        return self.error_code != ''

    @staticmethod
    def set_last_started(script):
        """
        Sets the last_ran flag for this script and disables the flag for all
        other scripts.

        Arguments
        ---------
        script: Script identifier
        """
        Script.objects.all().update(last_ran=False)
        Script.objects.filter(id=script).update(last_ran=True)

    @staticmethod
    def check_online(script):
        """
        Checks if all needed slaves are online.

        Returns
        -------
        Returns True if all needed slaves are online or if the script already
        run successful.
        """

        return not Program.objects.filter(
            scriptgraphprograms__script=script,
            slave__online=False,
        ).exists()

    @staticmethod
    def get_involved_slaves(script):
        """
        Returns all slaves which are involved.

        Returns
        -------
            A list of slaves
        """
        return Program.objects.filter(
            scriptgraphprograms__script=script).annotate(
                dcount=Count('slave')).values_list(
                    'slave',
                    flat=True,
                )


class ScriptGraphPrograms(Model):
    """
    Represents a dependency graph for programs in a script file.

    Members
    -------
        script: Script id
        index: Order in which the script starts
        program: Which program will be started
    """
    script = ForeignKey(Script, on_delete=CASCADE)
    index = IntegerField(null=False)
    program = ForeignKey(Program, on_delete=CASCADE)

    class Meta:
        unique_together = (('script', 'index', 'program'), )


class ScriptGraphFiles(Model):
    """
    Represents a dependency graph for filesystems in a script file.

    Members
    -------
        script: Script id
        index: Order in which the script starts
        filesystem: Which file will be move/delete/created
    """
    script = ForeignKey(Script, on_delete=CASCADE)
    index = IntegerField(null=False)
    filesystem = ForeignKey(Filesystem, on_delete=CASCADE)

    class Meta:
        unique_together = (('script', 'index', 'filesystem'), )


class ProgramStatus(Model):
    """
    Represents a process which is currently running on the slave.

    Members
    -------
        program: Program id
        code: last returned value of the program
        command_uuid: uuid of the send 'execute' request
        running: True if the program is currently running, otherwise False
        timeouted: True if the Timer function set this. Which means a
            start_time from program has elapsed.
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
