import json
from enum import Enum


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

    @classmethod
    def from_json(cls, string):
        data = json.loads(string)
        return cls(
            data['name'],
            [ScriptEntry(**program) for program in data['programs']],
        )

    def to_json(self):
        return json.dumps(self)


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

        if not isinstance(name, str):
            raise ValueError("Name has to be a string.")
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

    @classmethod
    def from_json(cls, string):
        data = json.loads(string)
        return cls(
            data['index'],
            data['name'],
            data['slave'],
            data['type'],
        )

    def to_json(self):
        return json.dumps(self)
