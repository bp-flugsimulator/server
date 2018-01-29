#  pylint: disable=C0111,C0103

from django.test import TestCase
from django.db.utils import IntegrityError

from frontend.scripts import Script, ScriptEntryFile, ScriptEntryProgram

from frontend.models import (
    Script as ScriptModel,
    ScriptGraphPrograms as SGP,
    ScriptGraphFiles as SGF,
)

from .factory import (
    SlaveFactory,
    ScriptFactory,
    ProgramFactory,
    FileFactory,
)


class ScriptTests(TestCase):  # pylint: disable=unused-variable
    def test_from_json_no_list(self):
        self.assertRaisesRegex(
            ValueError,
            "Files has to be a list",
            Script.from_json,
            '{"name": "test", "files": {}, "programs": []}',
        )

        self.assertRaisesRegex(
            ValueError,
            "Programs has to be a list",
            Script.from_json,
            '{"name": "test", "files": [], "programs": {}}',
        )

    def test_script_wrong_type_name(self):
        self.assertRaises(ValueError, Script, [], [], [])

    def test_script_wrong_type_program_not_a_list(self):
        self.assertRaises(ValueError, Script, "name", "not a list", [])

    def test_script_wrong_type_program_wrong_element(self):
        self.assertRaises(ValueError, Script, "name", ["String"], [])

    def test_script_wrong_type_file_not_a_list(self):
        self.assertRaises(ValueError, Script, "name", [], "not a list")

    def test_script_wrong_type_file_wrong_element(self):
        self.assertRaises(ValueError, Script, "name", [], ["String"])

    def test_script_entry_program_wrong_type_program(self):
        self.assertRaises(
            ValueError,
            ScriptEntryProgram,
            "a name",
            "whoops",
            0,
        )

    def test_script_entry_program_wrong_type_index(self):
        self.assertRaises(ValueError, ScriptEntryProgram, [], "whoops", 0)

    def test_script_entry_program_wrong_type_name(self):
        self.assertRaises(ValueError, ScriptEntryProgram, 0, [], 0)

    def test_script_entry_program_wrong_type_slave(self):
        self.assertRaises(ValueError, ScriptEntryProgram, 0, "", [])

    def test_script_wrong_file_type_program(self):
        self.assertRaises(ValueError, ScriptEntryFile, "a name", "whoops", 0)

    def test_script_entry_file_wrong_type_index(self):
        self.assertRaises(ValueError, ScriptEntryFile, [], "whoops", 0)

    def test_script_entry_file_wrong_type_name(self):
        self.assertRaises(ValueError, ScriptEntryFile, 0, [], 0)

    def test_script_entry_file_wrong_type_slave(self):
        self.assertRaises(ValueError, ScriptEntryFile, 0, "", [])

    def test_script_json(self):
        string = '{"name": "test", "files": [{"index": 0, "slave": 0, "file": "no name"}],\
            "programs": [{"index": 0, "slave": 0, "program": "no name"}]}'

        script = Script(
            "test",
            [ScriptEntryProgram(0, "no name", 0)],
            [ScriptEntryFile(0, "no name", 0)],
        )

        self.assertEqual(Script.from_json(string), script)
        self.assertEqual(Script.from_json(script.to_json()), script)

    def test_script_entry_program_json(self):
        string = '{"index": 0, "slave": 0, "program": "no name"}'

        script = ScriptEntryProgram(0, "no name", 0)

        self.assertEqual(ScriptEntryProgram.from_json(string), script)
        self.assertEqual(
            ScriptEntryProgram.from_json(script.to_json()),
            script,
        )

    def test_script_entry_file_json(self):
        string = '{"index": 0, "slave": 0, "file": "no name"}'

        script = ScriptEntryFile(0, "no name", 0)

        self.assertEqual(ScriptEntryFile.from_json(string), script)
        self.assertEqual(ScriptEntryFile.from_json(script.to_json()), script)

    def test_script_name_eq(self):
        self.assertNotEqual(
            Script("test", [ScriptEntryProgram(0, 0, 0)], []),
            Script("test2", [ScriptEntryProgram(0, 0, 0)], []),
        )

    def test_model_support_strings(self):
        slave = SlaveFactory()
        program = ProgramFactory(slave=slave)
        file = FileFactory(slave=slave)
        script_name = ScriptFactory.build().name

        Script(
            script_name,
            [ScriptEntryProgram(0, program.name, slave.name)],
            [ScriptEntryFile(0, file.name, slave.name)],
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
                file=file,
            ).exists())

    def test_model_support_ids(self):
        slave = SlaveFactory()
        program = ProgramFactory(slave=slave)
        file = FileFactory(slave=slave)
        script_name = ScriptFactory.build().name

        Script(
            script_name,
            [ScriptEntryProgram(0, int(program.id), int(slave.id))],
            [ScriptEntryFile(0, int(file.id), int(slave.id))],
        ).save()

        script = ScriptModel.objects.get(name=script_name)

        self.assertTrue(ScriptModel.objects.filter(name=script_name).exists())
        self.assertTrue(
            SGP.objects.filter(
                script=script,
                index=0,
                program=program,
            ).exists())

    def test_model_support_error_in_entry(self):
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

        self.assertRaisesRegex(
            ValueError,
            "Program with id {} does not exist.".format(program.id + 1),
            script.save,
        )
        self.assertFalse(ScriptModel.objects.filter(name=script_name).exists())
        self.assertTrue(len(SGP.objects.all()) == 0)

    def test_from_model_file_id_eq_str(self):
        file = FileFactory()
        slave = file.slave
        script = ScriptFactory()

        ScriptEntryFile(0, file.id, slave.id).save(script)
        b = ScriptEntryFile(0, file.name, slave.name)

        self.assertRaises(IntegrityError, b.save, script)

    def test_from_model_program_id_eq_str(self):
        program = ProgramFactory()
        slave = program.slave
        script = ScriptFactory()

        ScriptEntryProgram(0, program.id, slave.id).save(script)

        with_str = ScriptEntryProgram(
            0,
            program.name,
            slave.name,
        )

        self.assertRaises(IntegrityError, with_str.save, script)

    def test_from_query_error(self):
        class Dummy:
            def __init__(self):
                class Dummy:
                    def __init__(self):
                        class Dummy:
                            def __init__(self):
                                self.id = None

                        self.slave = Dummy()

                self.program = Dummy()
                self.file = Dummy()

        self.assertRaises(
            ValueError,
            ScriptEntryProgram.from_query,
            Dummy(),
            "not int",
            "not str",
        )
        self.assertRaises(
            ValueError,
            ScriptEntryProgram.from_query,
            Dummy(),
            "int",
            "not str",
        )

        self.assertRaises(
            ValueError,
            ScriptEntryFile.from_query,
            Dummy(),
            "not int",
            "not str",
        )
        self.assertRaises(
            ValueError,
            ScriptEntryFile.from_query,
            Dummy(),
            "int",
            "not str",
        )

    def test_script_get_slave(self):
        from frontend.scripts import get_slave
        self.assertEqual(None, get_slave(None))

    def test_script_name_is_string(self):
        self.assertRaisesRegex(
            ValueError,
            "Name has to be a string",
            Script,
            123123,
            [
                ScriptEntryProgram(0, 0, 0),
            ],
            [],
        )

    def test_script_positive_index(self):
        self.assertRaisesRegex(
            ValueError,
            "Use positive or null for the index.",
            ScriptEntryProgram,
            -1,
            0,
            0,
        )

        self.assertRaisesRegex(
            ValueError,
            "Use positive or null for the index.",
            ScriptEntryFile,
            -1,
            0,
            0,
        )

    def test_script_programs_missing_slave(self):
        slave = SlaveFactory()
        script = ScriptFactory()

        self.assertRaisesRegex(
            ValueError,
            "Program with id {} does not exist.".format(-1),
            ScriptEntryProgram(
                0,
                -1,
                int(slave.id),
            ).save,
            script,
        )

        self.assertRaisesRegex(
            ValueError,
            "Program with name {} does not exist.".format(""),
            ScriptEntryProgram(
                0,
                "",
                int(slave.id),
            ).save,
            script,
        )

        slave.delete()

        self.assertRaisesRegex(
            ValueError,
            "Client with name/id {} does not exist.".format(-1),
            ScriptEntryProgram(
                0,
                -1,
                -1,
            ).save,
            script,
        )

    def test_script_file_missing_slave(self):
        slave = SlaveFactory()
        script = ScriptFactory()

        self.assertRaisesRegex(
            ValueError,
            "File with id {} does not exist.".format(-1),
            ScriptEntryFile(
                0,
                -1,
                int(slave.id),
            ).save,
            script,
        )

        self.assertRaisesRegex(
            ValueError,
            "File with name {} does not exist.".format(""),
            ScriptEntryFile(
                0,
                "",
                int(slave.id),
            ).save,
            script,
        )

        slave.delete()

        self.assertRaisesRegex(
            ValueError,
            "Client with name/id {} does not exist.".format(-1),
            ScriptEntryFile(
                0,
                -1,
                -1,
            ).save,
            script,
        )
