"""
This module contains classes to translate from the script databasemodels
to javascript
"""

import json

from django.db import transaction

from .models import (
    Script as ScriptModel,
    ScriptGraphFiles as SGFModel,
    ScriptGraphPrograms as SGPModel,
    Program as ProgramModel,
    Filesystem as FilesystemModel,
    Slave as SlaveModel,
)


def get_slave(slave):
    """
    Checks if the given object is string or integer and queries the slave from
    that.

    Arguments
    ---------
        slave: slave name (string) or slave id (int)

    Returns
    -------
        Slave object if it is in the database or None if it is not string or
        int
    """
    if isinstance(slave, str):
        return SlaveModel.objects.get(name=slave)
    elif isinstance(slave, int):
        return SlaveModel.objects.get(id=slave)
    else:
        return None


class Script:
    """
    Fields
    ------
        name: Name of the script.
        programs: List of ScriptEntryProgram
        filesystems: List of ScriptGraphFiles
    """

    def __init__(self, name, programs, filesystems):
        if not isinstance(programs, list):
            raise ValueError("Program has to be a list.")
        for prog in programs:
            if not isinstance(prog, ScriptEntryProgram):
                raise ValueError(
                    "All list elements has to be ScriptEntryProgram.")
        self.programs = programs

        if not isinstance(filesystems, list):
            raise ValueError("filesystems has to be a list.")
        for filesystem in filesystems:
            if not isinstance(filesystem, ScriptEntryFile):
                raise ValueError(
                    "All list elements has to be ScriptEntryFile.")
        self.filesystems = filesystems

        if len(self.filesystems) + len(self.programs) < 1:
            raise ValueError("Add a filesystem or a program to the script.")

        if not isinstance(name, str):
            raise ValueError("Name has to be a string.")
        self.name = name

    def __eq__(self, other):
        if self.name != other.name:
            return False

        c_other_prog = list(other.programs)

        for item in self.programs:
            if item in c_other_prog:
                c_other_prog.remove(item)

        c_other_filesystem = list(other.filesystems)

        for item in self.filesystems:
            if item in c_other_filesystem:
                c_other_filesystem.remove(item)

        return len(c_other_prog) == 0 and len(c_other_filesystem) == 0

    def __iter__(self):
        yield ("name", self.name)
        yield ("programs", [dict(entry) for entry in self.programs])
        yield ("filesystems", [dict(entry) for entry in self.filesystems])

    @classmethod
    def from_model(cls, script_id, slaves_type, programs_type,
                   filesystem_type):
        """
        Creates a object from a script id.

        Arguments
        ---------
            scriptId: integer (identifier)

        Returns
        -------
            Script object

        """
        script = ScriptModel.objects.get(id=script_id)

        programs = [
            ScriptEntryProgram.from_query(model, slaves_type, programs_type)
            for model in SGPModel.objects.filter(script=script)
        ]
        filesystems = [
            ScriptEntryFile.from_query(model, slaves_type, filesystem_type)
            for model in SGFModel.objects.filter(script=script)
        ]

        return cls(script.name, programs, filesystems)

    @classmethod
    def from_json(cls, string):
        """
        Takes a JSON encoded string and build this object.

        Returns
        -------
            Script object
        """
        data = json.loads(string)

        if not isinstance(data['programs'], list):
            raise ValueError('Programs has to be a list')

        if not isinstance(data['filesystems'], list):
            raise ValueError('filesystems has to be a list')

        return cls(
            data['name'],
            [ScriptEntryProgram(**program) for program in data['programs']],
            [
                ScriptEntryFile(**filesystem)
                for filesystem in data['filesystems']
            ],
        )

    @transaction.atomic
    def save(self):
        """
        Saves this object to the database.
        """

        script = ScriptModel.objects.create(name=self.name)

        for obj in self.programs:
            obj.save(script)

        for obj in self.filesystems:
            obj.save(script)

    def to_json(self):
        """
        Converts this object to a JSON encoded string.

        Returns
        -------
            str
        """
        return json.dumps(dict(self))


class ScriptEntryFile:
    """
    Consists of the following fields

    Fields
    ------
        index: When will this script be started.
        filesystem: The name of the filesystem
        slave: Location of the filesystem
    """

    def __init__(self, index, filesystem, slave):
        if not isinstance(index, int):
            raise ValueError("Index has to be an integer.")
        if index < 0:
            raise ValueError("Use positive or null for the index.")
        self.index = index

        if not isinstance(filesystem, str) and not isinstance(filesystem, int):
            raise ValueError("Name has to be a string or int.")
        self.filesystem = filesystem

        if not isinstance(slave, str) and not isinstance(slave, int):
            raise ValueError("Slave has to be a string or integer")
        self.slave = slave

    def __eq__(self, other):
        return (self.index == other.index
                and self.filesystem == other.filesystem
                and self.slave == other.slave)

    def __iter__(self):
        for key, val in vars(self).items():
            yield (key, val)

    @classmethod
    def from_query(cls, query, slaves_type, programs_type):
        """
        Retrieves values from a django query (for ScriptGraphFiles or
        ScriptGraphPrograms).

        Arguments
        ----------
            query: django query

        Returns
        -------
             ScriptEntryFile object
        """

        if slaves_type == 'int':
            slave = query.filesystem.slave.id
        elif slaves_type == 'str':
            slave = query.filesystem.slave.name
        else:
            raise ValueError("Slave_type has to be int or str.")

        if programs_type == 'int':
            program = query.filesystem.id
        elif programs_type == 'str':
            program = query.filesystem.name
        else:
            raise ValueError("Program_type has to be int or str.")

        return cls(
            query.index,
            program,
            slave,
        )

    @classmethod
    def from_json(cls, string):
        """
        Takes a JSON encoded string and build this object.

        Returns
        -------
            Script object
        """
        data = json.loads(string)
        return cls(
            data['index'],
            data['filesystem'],
            data['slave'],
        )

    @transaction.atomic
    def save(self, script):
        """
        Transforms this object into ScriptGraphFiles and saves it to the
        database.

        Arguments
        ---------
            script: coresponding Script

        Returns
        -------
            Django model
        """

        try:
            slave = get_slave(self.slave)
        except SlaveModel.DoesNotExist:
            raise ValueError("Client with name/id {} does not exist.".format(
                self.slave))

        try:
            if isinstance(self.filesystem, str):
                obj = FilesystemModel.objects.get(
                    slave=slave, name=self.filesystem)
                SGFModel.objects.create(
                    script=script,
                    index=self.index,
                    filesystem=obj,
                )
        except FilesystemModel.DoesNotExist:
            raise ValueError("filesystem with name {} does not exist.".format(
                self.filesystem))

        try:
            if isinstance(self.filesystem, int):
                obj = FilesystemModel.objects.get(
                    slave=slave, id=self.filesystem)
                SGFModel.objects.create(
                    script=script,
                    index=self.index,
                    filesystem=obj,
                )
        except FilesystemModel.DoesNotExist:
            raise ValueError("filesystem with id {} does not exist.".format(
                self.filesystem))

    def to_json(self):
        """
        Converts this object to a JSON encoded string.

        Returns
        -------
            str
        """
        return json.dumps(dict(self))


class ScriptEntryProgram:
    """
    Consists of the following fields

    Fields
    ------
        index: When will this script be started.
        programs: The name of the program
        slave: Location of the program
    """

    def __init__(self, index, program, slave):
        if not isinstance(index, int):
            raise ValueError("Index has to be an integer.")
        if index < 0:
            raise ValueError("Use positive or null for the index.")
        self.index = index

        if not isinstance(program, str) and not isinstance(program, int):
            raise ValueError("Name has to be a string or int.")
        self.program = program

        if not isinstance(slave, str) and not isinstance(slave, int):
            raise ValueError("Slave has to be a string or integer")
        self.slave = slave

    def __eq__(self, other):
        return (self.index == other.index and self.program == other.program
                and self.slave == other.slave)

    def __iter__(self):
        for key, val in vars(self).items():
            yield (key, val)

    @classmethod
    def from_query(cls, query, slaves_type, programs_type):
        """
        Retrieves values from a django query (for ScriptGraphPrograms).

        Arguments
        ----------
            query: django query

        Returns
        -------
             ScriptEntry object
        """

        if slaves_type == 'int':
            slave = query.program.slave.id
        elif slaves_type == 'str':
            slave = query.program.slave.name
        else:
            raise ValueError("Slave_type has to be int or str.")

        if programs_type == 'int':
            program = query.program.id
        elif programs_type == 'str':
            program = query.program.name
        else:
            raise ValueError("Program_type has to be int or str.")

        return cls(
            query.index,
            program,
            slave,
        )

    def to_json(self):
        """
        Converts this object to a JSON encoded string.

        Returns
        -------
            str
        """
        return json.dumps(dict(self))

    @classmethod
    def from_json(cls, string):
        """
        Takes a JSON encoded string and build this object.

        Returns
        -------
            Script object
        """
        data = json.loads(string)
        return cls(
            data['index'],
            data['program'],
            data['slave'],
        )

    @transaction.atomic
    def save(self, script):
        """
        Transforms this object into ScriptGraphPrograms and saves it to the
        database.

        Arguments
        ---------
            script: coresponding Script

        Returns
        -------
            Django model
        """
        try:
            slave = get_slave(self.slave)
        except SlaveModel.DoesNotExist:
            raise ValueError("Client with name/id {} does not exist.".format(
                self.slave))

        try:
            if isinstance(self.program, str):
                obj = ProgramModel.objects.get(slave=slave, name=self.program)
                SGPModel.objects.create(
                    script=script,
                    index=self.index,
                    program=obj,
                )
        except ProgramModel.DoesNotExist:
            raise ValueError("Program with name {} does not exist.".format(
                self.program))

        try:
            if isinstance(self.program, int):
                obj = ProgramModel.objects.get(slave=slave, id=self.program)
                SGPModel.objects.create(
                    script=script,
                    index=self.index,
                    program=obj,
                )
        except ProgramModel.DoesNotExist:
            raise ValueError("Program with id {} does not exist.".format(
                self.program))
