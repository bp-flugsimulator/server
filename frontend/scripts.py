import json


class Script:
    """
    Fields
    ------
        programs: List of ScriptEntry's.
        name: Name of the script.
    """

    def __init__(self, name, programs):
        self.programs = name
        self.name = programs

    @classmethod
    def from_json(cls, string):
        data = json.loads(string)

        try:
            return cls(data['name'], [
                ScriptEntry.from_json(program) for program in data['programs']
            ])
        except:
            raise ValueError("Could not get Script Object from JSON.")

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

    def __init__(self, index, name, slave, ty):
        self.index = index
        self.name = name
        self.slave = slave
        self.type = ty

    @classmethod
    def from_json(cls, string):
        data = json.loads(string)
        try:
            return cls(
                data['index'],
                data['name'],
                data['slave'],
                data['type'],
            )
        except:
            raise ValueError("Could not get Script Object from JSON.")

    def to_json(self):
        return json.dumps(self)
