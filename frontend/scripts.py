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
    Filesystem as FilesystemModel,
    Slave as SlaveModel,
)

from .errors import (
    SlaveNotExistError,
    QueryParameterError,
    FilesystemNotExistError,
    ProgramNotExistError,
    PositiveNumberError,
)


def get_slave(slave):
    """
    Returns a `SlaveModel` based on the type of `slave`.

    Parameters
    ----------
        slave: int or str
            Identifies a `SlaveModel`

    Returns
    -------
        SlaveModel:
            Which has the name or id of `slave` based on the type.
    """
    if isinstance(slave, str):
        try:
            return SlaveModel.objects.get(name=slave)
        except SlaveModel.DoesNotExist as err:
            raise SlaveNotExistError(err, slave)
    elif isinstance(slave, int):
        try:
            return SlaveModel.objects.get(id=slave)
        except SlaveModel.DoesNotExist as err:
            raise SlaveNotExistError(err, slave)


class Script:
    """
    A intermediate representation for a script which comes in JSON encoded and
    needs to be saved into the database.

    Attributes
    ----------
        name: str
            Name of the `Script`.
        programs: list[ScriptEntryProgram]
            Which programs are in this `Script`.
        filesystems: list[ScriptEntryFilesystem]
            Which programs are in this `Script`.
    """

    def __init__(self, name, programs, filesystems):
        ensure_type("programs", programs, list)
        ensure_type_array("programs", programs, ScriptEntryProgram)
        self.programs = programs

        ensure_type("filesystems", filesystems, list)
        ensure_type_array("filesystem", filesystems, ScriptEntryFilesystem)
        self.filesystems = filesystems

        ensure_type("name", name, str)

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
        Creates a `Script` from a `ScriptModel` which is specified by
        `script_id`.

        Parameters
        ----------
            script_id: int
                The name of a valid `ScriptModel`.
            slaves_type: "str" or "int"
                The type of all slave attributes in this `Script`.
            programs_type: "str" or "int"
                The type of all slave attributes in this `Script`.
            filesystem_type: "str" or "int"
                The type of all slave attributes in this `Script`.

        Returns
        -------
        Script:
            A `Script` which is retreived from a `ScriptModel`.

        """
        script = ScriptModel.objects.get(id=script_id)

        programs = [
            ScriptEntryProgram.from_query(model, slaves_type, programs_type)
            for model in SGPModel.objects.filter(script=script)
        ]
        filesystems = [
            ScriptEntryFilesystem.from_query(model, slaves_type,
                                             filesystem_type)
            for model in SGFModel.objects.filter(script=script)
        ]

        return cls(script.name, programs, filesystems)

    @classmethod
    def from_json(cls, string):
        """
        Takes a JSON encoded string and build a `Script`.

        Parameters
        ----------
            string: str
                JSON encoded string.

        Returns
        -------
        Script:
            Which was paresed from the JSON encoded string.

        Raises
        ------
            TypeError:
                If programs and filesystems have the wrong type.
        """
        data = json.loads(string)

        ensure_type("programs", data["programs"], list)
        ensure_type("filesystems", data["filesystems"], list)

        ensure_type_array("programs", data["programs"], dict)
        ensure_type_array("filesystems", data["filesystems"], dict)

        return cls(
            data["name"],
            [ScriptEntryProgram(**program) for program in data["programs"]],
            [ScriptEntryFilesystem(**file) for file in data["filesystems"]],
        )

    @transaction.atomic
    def save(self):
        """
        This function coresspondes to the Django `Model.save` functionm,
        which saves the model to the database.
        """
        script = ScriptModel(name=self.name)
        script.full_clean()
        script.save()

        for obj in self.programs:
            obj.save(script)

        for obj in self.filesystems:
            obj.save(script)

    def to_json(self):
        """
        Converts this `Script` to a JSON encoded string.

        Returns
        -------
            str:
                JSON encoded string which contains the information from this
                `Script`.
        """
        return json.dumps(dict(self))


class ScriptEntryFilesystem:
    """
    Represents the `FilesystemModel` for a `Script`.

    Attributes
    ----------
        index: int
            The position in an ordered series
        filesystem: "int" or "str"
            The identifier of the filesystem
        slave: "int" or "str"
            Location of the filesystem
    """

    def __init__(self, index, filesystem, slave):
        ensure_type("index", index, int)

        if index < 0:
            raise PositiveNumberError(index, "index")
        self.index = index

        ensure_type("filesystem", filesystem, str, int)
        self.filesystem = filesystem

        ensure_type("slavesystem", slave, str, int)
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
        Retrieves all relevent attributes from a Django SQL query.

        Arguments
        ----------
            query: QuerySet
                A query which was run on the `ScriptGraphFilesModel`.

        Returns
        -------
        ScriptEntryFilesystem:
            If the query was valid.

        Raises
        ------
            QueryParameterError:
                If slaves_type or programs_type were not "str" or "int".
        """
        if slaves_type == "int":
            slave = query.filesystem.slave.id
        elif slaves_type == "str":
            slave = query.filesystem.slave.name
        else:
            raise QueryParameterError(
                slaves_type,
                ["int", "str"],
            )

        if programs_type == "int":
            program = query.filesystem.id
        elif programs_type == "str":
            program = query.filesystem.name
        else:
            raise QueryParameterError(
                programs_type,
                ["int", "str"],
            )

        return cls(
            query.index,
            program,
            slave,
        )

    @classmethod
    def from_json(cls, string):
        """
        Builds a `ScriptEntryFilesystem` from a JSON encoded string.

        Parameters
        ----------
            string: str
                A JSON encoded string which can be transfert into a
                `ScriptEntryFilesystem`.

        Returns
        -------
        ScriptEntryFilesystem:
            If the `ScriptEntryFilesystem` could be parsed from the JSON
            encoded string.
        """
        data = json.loads(string)
        return cls(
            data["index"],
            data["filesystem"],
            data["slave"],
        )

    @transaction.atomic
    def save(self, script):
        """
        This function coresspondes to the Django `Model.save` functionm,
        which saves the model to the database.

        Parameters
        ----------
            script: ScriptModel
                A valid `ScriptModel` which will be the reference for the
                `ScriptGraphFiles`.

        Raises
        ------
            FilesystemNotExistError
        """

        slave = get_slave(self.slave)

        try:
            if isinstance(self.filesystem, str):
                obj = FilesystemModel.objects.get(
                    slave=slave, name=self.filesystem)
                model = SGFModel(
                    script=script,
                    index=self.index,
                    filesystem=obj,
                )
                model.full_clean()
                model.save()
        except FilesystemModel.DoesNotExist as err:
            raise FilesystemNotExistError(err, self.filesystem)

        try:
            if isinstance(self.filesystem, int):
                obj = FilesystemModel.objects.get(
                    slave=slave, id=self.filesystem)
                model = SGFModel(
                    script=script,
                    index=self.index,
                    filesystem=obj,
                )
                model.full_clean()
                model.save()
        except FilesystemModel.DoesNotExist as err:
            raise FilesystemNotExistError(err, self.filesystem)

    def to_json(self):
        """
        Converts this `ScriptEntryFilesystem` to a JSON encoded string.

        Returns
        -------
            str:
                JSON encoded string which contains the information from this
                `ScriptEntryFilesystem`.
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
        ensure_type("index", index, int)

        if index < 0:
            raise PositiveNumberError(index, "index")
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
        if slaves_type == "int":
            slave = query.program.slave.id
        elif slaves_type == "str":
            slave = query.program.slave.name
        else:
            raise QueryParameterError(
                slaves_type,
                ["int", "str"],
            )

        if programs_type == "int":
            program = query.program.id
        elif programs_type == "str":
            program = query.program.name
        else:
            raise QueryParameterError(
                programs_type,
                ["int", "str"],
            )

        return cls(
            query.index,
            program,
            slave,
        )

    def to_json(self):
        """
        Converts this `ScriptEntryProgram` to a JSON encoded string.

        Returns
        -------
            str:
                JSON encoded string which contains the information from this
                `ScriptEntryProgram`.
        """
        return json.dumps(dict(self))

    @classmethod
    def from_json(cls, string):
        """
        Builds a `ScriptEntryProgram` from a JSON encoded string.

        Parameters
        ----------
            string: str
                A JSON encoded string which can be transfert into a
                `ScriptEntryProgram`.

        Returns
        -------
        ScriptEntryFilesystem:
            If the `ScriptEntryProgram` could be parsed from the JSON
            encoded string.
        """
        data = json.loads(string)
        return cls(
            data["index"],
            data["program"],
            data["slave"],
        )

    @transaction.atomic
    def save(self, script):
        """
        This function corresponds to the Django `Model.save` functionm,
        which saves the model to the database.

        Parameters
        ----------
            script: ScriptModel
                A valid `ScriptModel` which will be the reference for the
                `ScriptGraphPrograms`.

        Raises
        ------
            ProgramNotExistError
        """
        slave = get_slave(self.slave)

        try:
            if isinstance(self.program, str):
                obj = ProgramModel.objects.get(slave=slave, name=self.program)
                model = SGPModel(
                    script=script,
                    index=self.index,
                    program=obj,
                )
                model.full_clean()
                model.save()
        except ProgramModel.DoesNotExist as err:
            raise ProgramNotExistError(err, self.program)
        try:
            if isinstance(self.program, int):
                obj = ProgramModel.objects.get(slave=slave, id=self.program)
                model = SGPModel(
                    script=script,
                    index=self.index,
                    program=obj,
                )
                model.full_clean()
                model.save()
        except ProgramModel.DoesNotExist as err:
            raise ProgramNotExistError(err, self.program)
