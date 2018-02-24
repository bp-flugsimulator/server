"""
This module contains classes to translate from the script databasemodels
to javascript
"""

import json

from utils.typecheck import ensure_type, ensure_type_array

from django.db import transaction

from .models import (
    Script as ScriptModel,
    ScriptGraphFiles as SGFModel,
    ScriptGraphPrograms as SGPModel,
    Program as ProgramModel,
    File as FileModel,
    Slave as SlaveModel,
)


def get_slave(slave):
    """
    Checks if the given object is string or integer and queries the slave from that.

    Arguments
    ---------
        slave: slave name (string) or slave id (int)

    Returns
    -------
        A Slave objects
    """
    if isinstance(slave, str):
        try:
            return SlaveModel.objects.get(name=slave)
        except SlaveModel.DoesNotExist:
            raise ValueError(
                "The client with the name `{}` does not exist.".format(slave))
    elif isinstance(slave, int):
        try:
            return SlaveModel.objects.get(id=slave)
        except SlaveModel.DoesNotExist:
            raise ValueError(
                "The client with the id `{}` does not exist.".format(slave))


def typecheck_index(index):
    """
    Checks if the types are correct for an index variable.
    """
    ensure_type("index", index, int)
    if index < 0:
        raise ValueError("Only positive integers are allowed for index.")


class Script:
    """
    Fields
    ------
        name: Name of the script.
        programs: List of ScriptEntryProgram
        files: List of ScriptGraphFiles
    """

    def __init__(self, name, programs, files):
        ensure_type("programs", programs, list)
        ensure_type_array("programs", programs, ScriptEntryProgram)
        self.programs = programs

        ensure_type("files", files, list)
        ensure_type_array("files", files, ScriptEntryFile)
        self.files = files

        ensure_type("name", name, str)
        self.name = name

    def __eq__(self, other):
        if self.name != other.name:
            return False

        c_other_prog = list(other.programs)

        for item in self.programs:
            if item in c_other_prog:
                c_other_prog.remove(item)

        c_other_file = list(other.files)

        for item in self.files:
            if item in c_other_file:
                c_other_file.remove(item)

        return len(c_other_prog) == 0 and len(c_other_file) == 0

    def __iter__(self):
        yield ("name", self.name)
        yield ("programs", [dict(entry) for entry in self.programs])
        yield ("files", [dict(entry) for entry in self.files])

    @classmethod
    def from_model(cls, script_id, slaves_type, programs_type, file_type):
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
        files = [
            ScriptEntryFile.from_query(model, slaves_type, file_type)
            for model in SGFModel.objects.filter(script=script)
        ]

        return cls(script.name, programs, files)

    @classmethod
    def from_json(cls, string):
        """
        Takes a JSON encoded string and build this object.

        Returns
        -------
            Script object
        """
        data = json.loads(string)

        ensure_type("programs", data['programs'], list)
        ensure_type("files", data['files'], list)

        ensure_type_array("programs", data['programs'], dict)
        ensure_type_array("files", data['files'], dict)

        return cls(
            data['name'],
            [ScriptEntryProgram(**program) for program in data['programs']],
            [ScriptEntryFile(**file) for file in data['files']],
        )

    @transaction.atomic
    def save(self):
        """
        Saves this object to the database.
        """

        script = ScriptModel.objects.create(name=self.name)

        for obj in self.programs:
            obj.save(script)

        for obj in self.files:
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
        file: The name of the file
        slave: Location of the file
    """

    def __init__(self, index, file, slave):
        typecheck_index(index)
        self.index = index

        ensure_type("file", file, str, int)
        self.file = file

        ensure_type("slave", slave, str, int)
        self.slave = slave

    def __eq__(self, other):
        return (self.index == other.index and self.file == other.file
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
            slave = query.file.slave.id
        elif slaves_type == 'str':
            slave = query.file.slave.name
        else:
            raise ValueError("Slave_type has to be int or str.")

        if programs_type == 'int':
            program = query.file.id
        elif programs_type == 'str':
            program = query.file.name
        else:
            raise ValueError("File_type has to be int or str.")

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
            data['file'],
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

        slave = get_slave(self.slave)

        try:
            if isinstance(self.file, str):
                obj = FileModel.objects.get(slave=slave, name=self.file)
                SGFModel.objects.create(
                    script=script,
                    index=self.index,
                    file=obj,
                )
        except FileModel.DoesNotExist:
            raise ValueError("The file with name `{}` does not exist.".format(
                self.file))

        try:
            if isinstance(self.file, int):
                obj = FileModel.objects.get(slave=slave, id=self.file)
                SGFModel.objects.create(
                    script=script,
                    index=self.index,
                    file=obj,
                )
        except FileModel.DoesNotExist:
            raise ValueError("The file with id `{}` does not exist.".format(
                self.file))

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
        typecheck_index(index)
        self.index = index

        ensure_type("program", program, str, int)
        self.program = program

        ensure_type("slave", slave, str, int)
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
        slave = get_slave(self.slave)

        try:
            if isinstance(self.program, str):
                obj = ProgramModel.objects.get(slave=slave, name=self.program)
                SGPModel.objects.create(
                    script=script,
                    index=self.index,
                    program=obj,
                )
        except ProgramModel.DoesNotExist:
            raise ValueError("The program with name {} does not exist.".format(
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
            raise ValueError("The program with id {} does not exist.".format(
                self.program))
