from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


# Create your models here.
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


class Slave(models.Model):
    """
    Represents a slave which is node in the network.
    This is stored in a database.

    Attributes
    ----------
    id: int
        The unique ID which can be referenced to this object.

    name: str
        The name of the slave

    ip_address: GenericIPAddressField
        The IP address of the slave.

    mac_address: str
        The MAC address of the slave.

    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=200)
    ip_address = models.GenericIPAddressField(unique=True)
    mac_address = models.CharField(
        unique=True, max_length=17, validators=[validate_mac_address])


class Program(models.Model):
    """
    Represents a program on a slave
    This is stored in a database.

    Attributes
    ----------
    id: int
        The unique ID which can be referenced to this object.

    name: str
        The name of the program (has to be unique for every slave)

    path: str
        The path to the binaryfile that will be executed

    arguments: str
        The arguments which will be passed to the
        executable on execution

    slave: Slave
        The slave on which the command will be executed
    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(unique=False, max_length=200)
    path = models.CharField(unique=False, max_length=200)
    arguments = models.CharField(unique=False, blank=True, max_length=200)
    slave = models.ForeignKey(Slave, on_delete=models.CASCADE)

    class Meta:
        unique_together = (('name', 'slave'), )


class ProgramStatus(models.Model):
    """
    Represents a process which is currently running on the slave.

    Arguments
    ---------
        id: Program ID.
        error: Error message if the execution was not successful.
        started: Timestamp when the command was send.
        stopped: Timestamp when the result of the Command was received.
    """
    program = models.OneToOneField(
        Program,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    error = models.CharField(max_length=200, unique=False)
    started = models.DateTimeField(unique=False, blank=False)
    stopped = models.DateTimeField(unique=False)


class SlaveStatus(models.Model):
    """
    Represents the current status of the slaves.

    Arguments
    ---------
        id: Slave ID.
        booted: Timestamp, when the slave was started via uptime command
        online: If the Slave has connected to the server.
    """
    slave = models.OneToOneField(
        Slave,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    boottime = models.DateTimeField(unique=False)
    reply_channel = models.CharField(max_length=200)
