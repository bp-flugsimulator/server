import json
from enum import Enum
from django.db import transaction
from .models import Script as ScriptModel
from .models import ScriptGraphFiles as SGFModel, ScriptGraphPrograms as SGPModel, Program as ProgramModel, File as FileMode, Slave as SlaveModel


class Script:
    """
    Fields
    ------
        name: Name of the script.
        programs: List of ScriptEntry's.
    """

    def __init__(self, name, programs):
        if not isinstance(programs, list):
            raise ValueError("Program has to be a list.")
        self.programs = programs

        if not isinstance(name, str):
            raise ValueError("Name has to be a string.")
        self.name = name

    def __eq__(self, other):
        if self.name != other.name:
            return False

        c_other = list(other.programs)

        for item in self.programs:
            if item in c_other:
                c_other.remove(item)

        return len(c_other) == 0

    def __iter__(self):
        yield ("name", self.name)
        yield ("programs", [dict(entry) for entry in self.programs])

    @classmethod
    def from_model(cls, scriptId):
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
            ScriptEntry.from_query(model)
            for model in SGPModel.objects.filter(script=script)
        ]
        b = [
            ScriptEntry.from_query(model)
            for model in SGFModel.objects.filter(script=script)
        ]

        return cls(script.name, a + b)

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
            [ScriptEntry(**program) for program in data['programs']],
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

            for prog in programs:
                prog.save()

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


class ScriptEntry:
    """
    Consists of the following fields

    Fields
    ------
        index: When will this script be started.
        name: The name of the program/file
        slave: Location of the program/file
        type: The type program/file.
    """

    TABLE_TYPES = ["program", "file"]

    def __init__(self, index, name, slave, type):
        if not isinstance(index, int):
            raise ValueError("Index has to be an integer.")
        self.index = index

        if not isinstance(name, str) and not isinstance(name, int):
            raise ValueError("Name has to be a string or int.")
        self.name = name

        if not isinstance(slave, str) and not isinstance(slave, int):
            raise ValueError("Slave has to be a string or integer")
        self.slave = slave

        if type not in self.TABLE_TYPES:
            raise ValueError("ty is not in TABLE_TYPES={}".format(
                self.TABLE_TYPES))
        self.type = type

    def __eq__(self, other):
        return self.index == other.index and self.name == other.name and self.slave == other.slave and self.type == other.type

    def __iter__(self):
        for k, v in vars(self).items():
            yield (k, v)

    @classmethod
    def from_query(cls, query):
        """
        Retrieves values from a django query (for ScriptGraphFiles or ScriptGraphPrograms).

        Arguments
        ----------
            query: django query

        Returns
        -------
             ScriptEntry object
        """
        if hasattr(query, "file"):
            return cls(
                query.index,
                query.file.id,
                query.file.slave,
                "file",
            )
        elif hasattr(query, "program"):
            return cls(
                query.index,
                query.program.id,
                query.program.slave.id,
                "program",
            )
        else:
            raise ValueError("Not supported query input.")

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
            data['type'],
        )

    def as_model(self, script):
        """
        Transforms this object into ScriptGraphFiles or ScriptGraphPrograms depending
        on the given type.

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
        else:
            raise ValueError("Not supported value")

        if self.type == 'program':
            if isinstance(self.name, str):
                obj = ProgramModel.objects.get(slave=slave, name=self.name)
            elif isinstance(self.name, int):
                obj = ProgramModel.objects.get(slave=slave, id=self.name)
            else:
                raise ValueError("Not supported value")

            return SGPModel(script=script, index=self.index, program=obj)
        elif self.type == 'file':
            if isinstance(self.name, str):
                obj = FileModel.objects.get(
                    slave=slave, name=self.name).distinct()
            elif isinstance(self.name, int):
                obj = FileModel.objects.get(
                    slave=slave, id=self.name).distinct()
            else:
                raise ValueError("Not supported value")

            return SGFModel(script=script, index=self.index, file=obj)
        else:
            raise ValueError("Not supported value")

    def to_json(self):
        """
        Converts this object to a JSON encoded string.

        Returns
        -------
            str
        """
        return json.dumps(dict(self))
