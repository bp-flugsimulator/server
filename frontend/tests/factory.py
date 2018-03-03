"""
Database factories for tests
"""
import socket
import struct
from uuid import uuid4
from factory import SubFactory, Sequence, LazyAttribute
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyText, FuzzyInteger

from frontend.models import (
    Slave as SlaveModel,
    ProgramStatus as ProgramStatusModel,
    Program as ProgramModel,
    Script as ScriptModel,
    ScriptGraphPrograms as SGP,
    ScriptGraphFiles as SGF,
    Filesystem as FilesystemModel,
)


def int_to_mac(integer):
    """
    Converts a an integer into a mac address, with `:` notation.

    Arguments
    ---------
        integer: int

    Returns
    -------
        str
    """
    first = "{:012x}".format(integer)[::2]
    second = "{:012x}".format(integer)[1::2]

    return ':'.join(a + b for a, b in zip(first, second))


class SlaveFactory(DjangoModelFactory):
    class Meta:
        model = SlaveModel

    name = FuzzyText(length=20, prefix="slave_")
    ip_address = Sequence(lambda n: socket.inet_ntoa(struct.pack('!L', n)))
    mac_address = Sequence(int_to_mac)


class SlaveOnlineFactory(DjangoModelFactory):
    class Meta:
        model = SlaveModel

    name = FuzzyText(length=20, prefix="slave_")
    ip_address = Sequence(lambda n: socket.inet_ntoa(struct.pack('!L', n)))
    mac_address = Sequence(int_to_mac)
    online = True
    command_uuid = LazyAttribute(lambda a: uuid4().hex)


class ProgramFactory(DjangoModelFactory):
    class Meta:
        model = ProgramModel

    name = FuzzyText(length=20, prefix="program_")
    path = FuzzyText(length=40)
    arguments = FuzzyText(length=200)
    slave = SubFactory(SlaveFactory)
    start_time = FuzzyInteger(0)


class ProgramStatusFactory(DjangoModelFactory):
    class Meta:
        model = ProgramStatusModel

    program = SubFactory(ProgramFactory)
    command_uuid = LazyAttribute(lambda a: uuid4().hex)
    running = False
    code = ""


class FileFactory(DjangoModelFactory):
    class Meta:
        model = FilesystemModel

    name = FuzzyText(length=20, prefix="file_")
    source_path = FuzzyText(length=100)
    source_type = 'file'
    destination_path = FuzzyText(length=100)
    destination_type = 'file'
    slave = SubFactory(SlaveFactory)
    command_uuid = LazyAttribute(lambda a: uuid4().hex)


class MovedFileFactory(DjangoModelFactory):
    class Meta:
        model = FilesystemModel

    name = FuzzyText(length=20, prefix="file_")
    source_path = FuzzyText(length=100)
    destination_path = FuzzyText(length=100)
    slave = SubFactory(SlaveFactory)
    command_uuid = LazyAttribute(lambda a: uuid4().hex)
    hash_value = FuzzyText(length=20, prefix="file_")


class ScriptFactory(DjangoModelFactory):
    class Meta:
        model = ScriptModel

    name = FuzzyText(length=20, prefix="script_")


class SGPFactory(DjangoModelFactory):
    class Meta:
        model = SGP

    index = FuzzyInteger(0)


class SGFFactory(DjangoModelFactory):
    class Meta:
        model = SGF

    index = FuzzyInteger(0)
