"""
This module contains all databasemodels from the frontend application.
"""

from django.db.models import Model, CharField, GenericIPAddressField,\
    ForeignKey, CASCADE, IntegerField, BooleanField, OneToOneField
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


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


class Slave(Model):
    """
    Represents a slave which is node in the network.
    This is stored in a database.

    Members
    -------
    name: str
        The name of the slave

    ip_address: GenericIPAddressField
        The IP address of the slave.

    mac_address: str
        The MAC address of the slave.

    """
    name = CharField(unique=True, max_length=200)
    ip_address = GenericIPAddressField(unique=True)
    mac_address = CharField(
        unique=True, max_length=17, validators=[validate_mac_address])

    @property
    def is_online(self):
        """
        Returns true of the current slave has connected to the master.
        """
        try:
            return self.slavestatus.online
        except SlaveStatus.DoesNotExist:
            return False

    @property
    def has_error(self):
        """
        Returns true if any program or file is in an error state.
        """
        for prog in self.program_set.all():
            if prog.is_error:
                return True

        return False

    @property
    def has_running(self):
        """
        Returns true if any program or file is in an error state.
        """
        for prog in self.program_set.all():
            if prog.is_running:
                return True

        return False


class Program(Model):
    """
    Represents a program on a slave
    This is stored in a database.

    Members
    -------
    name: str
        The name of the program (has to be unique for every slave)

    path: str
        The path to the binary file that will be executed

    arguments: str
        The arguments which will be passed to the
        executable on execution

    slave: Slave
        The slave on which the command will be executed
    """
    name = CharField(unique=False, max_length=200)
    path = CharField(unique=False, max_length=200)
    arguments = CharField(unique=False, blank=True, max_length=200)
    slave = ForeignKey(Slave, on_delete=CASCADE)

    class Meta:
        unique_together = (('name', 'slave'), )

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
        Returns true if the current program was executed not successful, which means the error code was 0.
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


class File(Model):
    """
    Represents a file on a slave
    This is stored in a database.

    Members
    -------
    name: str
        The name of the file (has to be unique for every slave)

    sourcePath: str
        The path to the source of the file

    destinationPath: str
        The path there the file should be used in the file system

    slave: Slave
        The slave on which the file belongs to
    """
    name = CharField(unique=False, max_length=200)
    sourcePath = CharField(unique=False, max_length=200)
    destinationPath = CharField(unique=False, max_length=200)
    slave = ForeignKey(Slave, on_delete=CASCADE)

    class Meta:
        unique_together = (('name', 'slave'), )


class Script(Model):
    """
    Represents a script file in a json format.

    Members
    -------
    name: str
        The name of the script (has to be unique for every slave)
    """
    name = CharField(unique=True, max_length=200)


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
    Represents a dependency graph for files in a script file.

    Members
    -------
        script: Script id
        index: Order in which the script starts
        file: Which file will be move/delete/created
    """
    script = ForeignKey(Script, on_delete=CASCADE)
    index = IntegerField(null=False)
    file = ForeignKey(File, on_delete=CASCADE)

    class Meta:
        unique_together = (('script', 'index', 'file'), )


class ProgramStatus(Model):
    """
    Represents a process which is currently running on the slave.

    Members
    -------
        program: Program id
        code: last returned value of the program
        command_uuid: uuid of the send 'execute' request
        running: True if the program is currently running, otherwise False
    """
    program = OneToOneField(
        Program,
        on_delete=CASCADE,
        primary_key=True,
    )
    code = CharField(max_length=200, unique=False, blank=True)
    command_uuid = CharField(max_length=32, unique=True)
    running = BooleanField(unique=False, default=True)


class SlaveStatus(Model):
    """
    Represents the current status of the slaves.

    Members
    -------
        slave: Slave id
        command_uuid: uuid of the send 'online' request
        online: true if the slave is currently online, otherwise false
    """
    slave = OneToOneField(
        Slave,
        on_delete=CASCADE,
        primary_key=True,
    )
    command_uuid = CharField(max_length=32, unique=True)
    online = BooleanField(unique=False, default=False)
