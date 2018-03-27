"""
Test cases for the script.py module.
"""
# pylint: disable=missing-docstring,too-many-public-methods

from django.test import TestCase
from django.core.exceptions import ValidationError

from frontend.scripts import (
    Script,
    ScriptEntryFilesystem,
    ScriptEntryProgram,
    get_slave,
)

from frontend.models import (
    Script as ScriptModel,
    ScriptGraphPrograms as SGP,
    ScriptGraphFiles as SGF,
)

from frontend.errors import (
    SlaveNotExistError,
    ProgramNotExistError,
    QueryParameterError,
    FilesystemNotExistError,
    PositiveNumberError,
)

from .factory import (
    SlaveFactory,
    ScriptFactory,
    ProgramFactory,
    FileFactory,
)


class ScriptTests(TestCase):
    def test_get_slave_none(self):
        self.assertEqual(None, get_slave(None))

    def test_get_slave_int(self):
        slave = SlaveFactory()
        self.assertEqual(get_slave(slave.id), slave)

    def test_get_slave_str(self):
        slave = SlaveFactory()

        self.assertEqual(get_slave(slave.name), slave)

    def test_get_slave_str_not_found(self):
        self.assertRaises(
            SlaveNotExistError,
            get_slave,
            "empty",
        )

    def test_get_slave_int_not_found(self):
        self.assertRaises(
            SlaveNotExistError,
            get_slave,
            -1,
        )

    def test_from_json(self):
        string = '{"name": "test", "filesystems": [{"index": 0, "slave": 0, "filesystem": \
            "no name"}], "programs": [{"index": 0, "slave": 0, \
            "program": "no name"}]}'

        script = Script(
            "test",
            [ScriptEntryProgram(0, "no name", 0)],
            [ScriptEntryFilesystem(0, "no name", 0)],
        )

        self.assertEqual(Script.from_json(string), script)
        self.assertEqual(Script.from_json(script.to_json()), script)

    def test_from_json_program(self):
        string = '{"index": 0, "slave": 0, "program": "no name"}'

        script = ScriptEntryProgram(0, "no name", 0)

        self.assertEqual(ScriptEntryProgram.from_json(string), script)
        self.assertEqual(
            ScriptEntryProgram.from_json(script.to_json()),
            script,
        )

    def test_from_json_file(self):
        string = '{"index": 0, "slave": 0, "filesystem": "no name"}'

        script = ScriptEntryFilesystem(0, "no name", 0)

        self.assertEqual(ScriptEntryFilesystem.from_json(string), script)
        self.assertEqual(
            ScriptEntryFilesystem.from_json(script.to_json()), script)

    def test_name_not_equal(self):
        self.assertNotEqual(
            Script("test", [ScriptEntryProgram(0, 0, 0)], []),
            Script("test2", [ScriptEntryProgram(0, 0, 0)], []),
        )

    def test_string_identifiers(self):
        slave = SlaveFactory()
        program = ProgramFactory(slave=slave)
        filesystem = FileFactory(slave=slave)
        script_name = ScriptFactory.build().name

        Script(
            script_name,
            [ScriptEntryProgram(0, program.name, slave.name)],
            [ScriptEntryFilesystem(0, filesystem.name, slave.name)],
        ).save()

        script = ScriptModel.objects.get(name=script_name)

        self.assertTrue(ScriptModel.objects.filter(name=script_name).exists())
        self.assertTrue(
            SGP.objects.filter(
                script=script,
                index=0,
                program=program,
            ).exists())

        self.assertTrue(
            SGF.objects.filter(
                script=script,
                index=0,
                filesystem=filesystem,
            ).exists())

    def test_integer_identifiers(self):
        slave = SlaveFactory()
        program = ProgramFactory(slave=slave)
        filesystem = FileFactory(slave=slave)
        script_name = ScriptFactory.build().name

        Script(
            script_name,
            [ScriptEntryProgram(0, int(program.id), int(slave.id))],
            [ScriptEntryFilesystem(0, int(filesystem.id), int(slave.id))],
        ).save()

        script = ScriptModel.objects.get(name=script_name)

        self.assertTrue(ScriptModel.objects.filter(name=script_name).exists())
        self.assertTrue(
            SGP.objects.filter(
                script=script,
                index=0,
                program=program,
            ).exists())

    def test_program_not_exist(self):
        program = ProgramFactory()
        slave = program.slave
        script_name = ScriptFactory.build().name

        script = Script(
            script_name,
            [
                ScriptEntryProgram(0, program.id, slave.id),
                ScriptEntryProgram(0, program.id + 1, slave.id),
            ],
            [],
        )

        self.assertRaises(
            ProgramNotExistError,
            script.save,
        )

        self.assertFalse(ScriptModel.objects.filter(name=script_name).exists())
        self.assertTrue(len(SGP.objects.all()) == 0)

    def test_model_references_same_str(self):
        filesystem = FileFactory()
        slave = filesystem.slave
        script = ScriptFactory()

        ScriptEntryFilesystem(0, filesystem.id, slave.id).save(script)
        b = ScriptEntryFilesystem(0, filesystem.name, slave.name)

        self.assertRaises(ValidationError, b.save, script)

    def test_model_references_same_int(self):
        program = ProgramFactory()
        slave = program.slave
        script = ScriptFactory()

        ScriptEntryProgram(0, program.id, slave.id).save(script)

        with_str = ScriptEntryProgram(
            0,
            program.name,
            slave.name,
        )

        self.assertRaises(
            ValidationError,
            with_str.save,
            script,
        )

    def test_from_query_error(self):
        class Dummy:
            def __init__(self):
                class Dummy:
                    def __init__(self):
                        class Dummy:
                            def __init__(self):
                                self.id = None
                                self.name = None

                        self.slave = Dummy()

                self.program = Dummy()
                self.filesystem = Dummy()

        self.assertRaises(
            QueryParameterError,
            ScriptEntryProgram.from_query,
            Dummy(),
            "not int",
            "not str",
        )
        self.assertRaises(
            QueryParameterError,
            ScriptEntryProgram.from_query,
            Dummy(),
            "int",
            "not str",
        )

        self.assertRaises(
            QueryParameterError,
            ScriptEntryFilesystem.from_query,
            Dummy(),
            "not int",
            "not str",
        )
        self.assertRaises(
            QueryParameterError,
            ScriptEntryFilesystem.from_query,
            Dummy(),
            "int",
            "not str",
        )

    def test_positive_index_error(self):
        self.assertRaises(
            PositiveNumberError,
            ScriptEntryProgram,
            -1,
            0,
            0,
        )

        self.assertRaises(
            PositiveNumberError,
            ScriptEntryFilesystem,
            -1,
            0,
            0,
        )

    def test_program_slave_not_exist_error(self):
        slave = SlaveFactory()
        script = ScriptFactory()

        self.assertRaises(
            ProgramNotExistError,
            ScriptEntryProgram(
                0,
                -1,
                int(slave.id),
            ).save,
            script,
        )

        self.assertRaises(
            ProgramNotExistError,
            ScriptEntryProgram(
                0,
                "",
                int(slave.id),
            ).save,
            script,
        )

        slave.delete()

        self.assertRaises(
            SlaveNotExistError,
            ScriptEntryProgram(
                0,
                -1,
                -1,
            ).save,
            script,
        )

    def test_file_slave_not_exist_error(self):
        slave = SlaveFactory()
        script = ScriptFactory()

        self.assertRaises(
            FilesystemNotExistError,
            ScriptEntryFilesystem(
                0,
                -1,
                int(slave.id),
            ).save,
            script,
        )

        self.assertRaises(
            FilesystemNotExistError,
            ScriptEntryFilesystem(
                0,
                "",
                int(slave.id),
            ).save,
            script,
        )

        slave.delete()

        self.assertRaises(
            SlaveNotExistError,
            ScriptEntryFilesystem(
                0,
                -1,
                -1,
            ).save,
            script,
        )
