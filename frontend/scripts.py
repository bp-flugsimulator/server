import json
from enum import Enum
from django.db import transaction
from .models import Script as ScriptModel
from .models import ScriptGraphFiles as SGFModel, ScriptGraphPrograms as SGPModel, Program as ProgramModel, File as FileModel, Slave as SlaveModel


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
    def from_model(cls, scriptId, slaves_type, programs_type):
        """
        Creates a object from a script id.

        Arguments
        ---------
            scriptId: integer (identifier)

        Returns
        -------
            Script object

        """
        script = ScriptModel.objects.get(id=scriptId)

        a = [
            ScriptEntryProgram.from_query(model, slaves_type, programs_type)
            for model in SGPModel.objects.filter(script=script)
        ]
        b = [
            ScriptEntryFile.from_query(model, slaves_type, programs_type)
            for model in SGFModel.objects.filter(script=script)
        ]

        return cls(script.name, a, b)

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
            data['name'],
            [ScriptEntryProgram(**program) for program in data['programs']],
            [ScriptEntryFile(**file) for file in data['files']],
        )

    def save(self):
        """
        Saves this object to the database.
        """

        first = transaction.savepoint()

        script = ScriptModel(name=self.name)
        script.save()

        try:
            programs = [obj.as_model(script) for obj in self.programs]
            files = [obj.as_model(script) for obj in self.files]

            for prog in programs:
                prog.save()

            for fil in files:
                fil.save()

            transaction.savepoint_commit(first)
        except Exception as err:
            transaction.savepoint_rollback(first)
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
        name: The name of the program/file
        slave: Location of the program/file
    """

    def __init__(self, index, name, slave):
        if not isinstance(index, int):
            raise ValueError("Index has to be an integer.")
        self.index = index

        if not isinstance(name, str) and not isinstance(name, int):
            raise ValueError("Name has to be a string or int.")
        self.name = name

        if not isinstance(slave, str) and not isinstance(slave, int):
            raise ValueError("Slave has to be a string or integer")
        self.slave = slave

    def __eq__(self, other):
        return self.index == other.index and self.name == other.name and self.slave == other.slave

    def __iter__(self):
        for k, v in vars(self).items():
            yield (k, v)

    @classmethod
    def from_query(cls, query, slaves_type, programs_type):
        """
        Retrieves values from a django query (for ScriptGraphFiles or ScriptGraphPrograms).

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
            data['name'],
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
        if isinstance(self.slave, str):
            slave = SlaveModel.objects.get(name=self.slave)
        elif isinstance(self.slave, int):
            slave = SlaveModel.objects.get(id=self.slave)

        if isinstance(self.name, str):
            obj = FileModel.objects.get(slave=slave, name=self.name)
        elif isinstance(self.name, int):
            obj = FileModel.objects.get(slave=slave, id=self.name)

        return SGFModel(script=script, index=self.index, file=obj)

    def to_json(self):
        """
        Converts this object to a JSON encoded string.

        Returns
        -------
            str
        """
        return json.dumps(dict(self))


class ScriptEntryProgram:
    def __init__(self, index, name, slave):
        if not isinstance(index, int):
            raise ValueError("Index has to be an integer.")
        self.index = index

        if not isinstance(name, str) and not isinstance(name, int):
            raise ValueError("Name has to be a string or int.")
        self.name = name

        if not isinstance(slave, str) and not isinstance(slave, int):
            raise ValueError("Slave has to be a string or integer")
        self.slave = slave

    def __eq__(self, other):
        return self.index == other.index and self.name == other.name and self.slave == other.slave

    def __iter__(self):
        for k, v in vars(self).items():
            yield (k, v)

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
            data['name'],
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
        if isinstance(self.slave, str):
            slave = SlaveModel.objects.get(name=self.slave)
        elif isinstance(self.slave, int):
            slave = SlaveModel.objects.get(id=self.slave)

        if isinstance(self.name, str):
            obj = ProgramModel.objects.get(slave=slave, name=self.name)
        elif isinstance(self.name, int):
            obj = ProgramModel.objects.get(slave=slave, id=self.name)

        return SGPModel(script=script, index=self.index, program=obj)
