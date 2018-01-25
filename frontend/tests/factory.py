from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyText, FuzzyInteger
from factory import SubFactory, Sequence
from uuid import uuid4

import socket, struct

from frontend.models import (
    Slave as SlaveModel,
    SlaveStatus as SlaveStatusModel,
    ProgramStatus as ProgramStatusModel,
    Program as ProgramModel,
    Script as ScriptModel,
    ScriptGraphPrograms as SGP,
    ScriptGraphFiles as SGF,
    File as FileModel,
)


class SlaveFactory(DjangoModelFactory):
    class Meta:
        model = SlaveModel

    name = FuzzyText(length=20, prefix="slave_")
    ip_address = Sequence(lambda n: socket.inet_ntoa(struct.pack('!L', n)))
    mac_address = Sequence(lambda n: ':'.join(a+b for a,b in zip("{:012x}".format(n)[::2], "{:012x}".format(n)[1::2])))


class SlaveStatusFactory(DjangoModelFactory):
    class Meta:
        model = SlaveStatusModel

    slave = SubFactory(SlaveFactory)
    command_uuid = uuid4().hex
    online = False


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
    command_uuid = uuid4().hex
    running = False
    code = ""


class FileFactory(DjangoModelFactory):
    class Meta:
        model = FileModel

    name = FuzzyText(length=20, prefix="file_")
    sourcePath = FuzzyText(length=100)
    destinationPath = FuzzyText(length=100)
    slave = SubFactory(SlaveFactory)


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
