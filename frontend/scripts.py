"""
This module contains classes to translate from the script databasemodels
to javascript
"""

import json
from .models import Script as ScriptModel
from .models import (
    ScriptGraphFiles as SGFModel,
    ScriptGraphPrograms as SGPModel,
    Program as ProgramModel,
    File as FileModel,
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
        files: List of ScriptGraphFiles
    """

    def __init__(self, name, programs, files):
        if not isinstance(programs, list):
            raise ValueError("Program has to be a list.")
        for prog in programs:
            if not isinstance(prog, ScriptEntryProgram):
                raise ValueError(
                    "All list elements has to be ScriptEntryProgram.")
        self.programs = programs

        if not isinstance(files, list):
            raise ValueError("Files has to be a list.")
        for file in files:
            if not isinstance(file, ScriptEntryFile):
                raise ValueError(
                    "All list elements has to be ScriptEntryFile.")
        self.files = files

        if len(self.files) + len(self.programs) < 1:
            raise ValueError("Add a file or a program to the script.")

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

        if not isinstance(data['programs'], list):
            raise ValueError('Programs has to be a list')

        if not isinstance(data['files'], list):
            raise ValueError('Files has to be a list')

        return cls(
            data['name'],
            [ScriptEntryProgram(**program) for program in data['programs']],
            [ScriptEntryFile(**file) for file in data['files']],
        )

    def save(self):
        """
        Saves this object to the database.
        """

        script = ScriptModel(name=self.name)
        script.save()

        done = []

        try:
            programs = [obj.as_model(script) for obj in self.programs]

            for prog in programs:
                prog.save()
                done.append(prog)

            files = [obj.as_model(script) for obj in self.files]
            for fil in files:
                fil.save()
                done.append(fil)

        except Exception as err:
            script.delete()

            for did in done:
                did.delete()

            raise err

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
        if not isinstance(index, int):
            raise ValueError("Index has to be an integer.")
        if index < 0:
            raise ValueError("Use positive or null for the index.")
        self.index = index

        if not isinstance(file, str) and not isinstance(file, int):
            raise ValueError("Name has to be a string or int.")
        self.file = file

        if not isinstance(slave, str) and not isinstance(slave, int):
            raise ValueError("Slave has to be a string or integer")
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
            data['file'],
            data['slave'],
        )

    def as_model(self, script):
        """
        Transforms this object into ScriptGraphFiles.

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
            if isinstance(self.file, str):
                obj = FileModel.objects.get(slave=slave, name=self.file)
                return SGFModel(script=script, index=self.index, file=obj)
        except FileModel.DoesNotExist:
            raise ValueError("File with name {} does not exist.".format(
                self.file))

        try:
            if isinstance(self.file, int):
                obj = FileModel.objects.get(slave=slave, id=self.file)
                return SGFModel(script=script, index=self.index, file=obj)
        except FileModel.DoesNotExist:
            raise ValueError("File with id {} does not exist.".format(
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

    def as_model(self, script):
        """
        Transforms this object into ScriptGraphPrograms.

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
                return SGPModel(script=script, index=self.index, program=obj)
        except ProgramModel.DoesNotExist:
            raise ValueError("Program with name {} does not exist.".format(
                self.program))

        try:
            if isinstance(self.program, int):
                obj = ProgramModel.objects.get(slave=slave, id=self.program)
                return SGPModel(script=script, index=self.index, program=obj)
        except ProgramModel.DoesNotExist:
            raise ValueError("Program with id {} does not exist.".format(
                self.program))
