#  pylint: disable=C0111,C0103

import json
import os

from urllib.parse import urlencode
from shlex import split

from django.test import TestCase
from django.urls import reverse
from channels.test import WSClient

from utils import Status, Command
from frontend.scripts import Script, ScriptEntryFile, ScriptEntryProgram

from frontend.models import (
    Script as ScriptModel,
    Slave as SlaveModel,
    Filesystem as FilesystemModel,
    Program as ProgramModel,
    ProgramStatus as ProgramStatusModel,
)

from frontend.errors import (
    SlaveOfflineError,
    SlaveNotExistError,
    ProgramNotExistError,
    ProgramNotRunningError,
    ProgramRunningError,
    FilesystemMovedError,
    FilesystemNotMovedError,
)

from .factory import (
    SlaveFactory,
    SlaveOnlineFactory,
    ProgramFactory,
    ScriptFactory,
    FileFactory,
    MovedFileFactory,
    ProgramStatusFactory,
)

from .testcases import StatusTestCase


class ScriptTest(TestCase):
    def test_script_run_forbidden(self):
        response = self.client.put("/api/script/0/run")
        self.assertEqual(response.status_code, 403)

    def test_script_run_get_unknown_scriptlave(self):
        response = self.client.get("/api/script/0/run")
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "The script with the id 0 does not exist",
        )

    def test_script_delete(self):
        slave = SlaveFactory()
        program = ProgramFactory(slave=slave)
        filesystem = FileFactory(slave=slave)
        script_name = ScriptFactory.build().name

        script = Script(
            script_name,
            [ScriptEntryProgram(0, program.name, slave.name)],
            [ScriptEntryFile(0, filesystem.name, slave.name)],
        )
        script.save()

        db_script = ScriptModel.objects.get(name=script_name)

        response = self.client.delete("/api/script/" + str(db_script.id))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ScriptModel.objects.filter(name=script_name).exists())

    def test_add_script_forbidden(self):
        response = self.client.put("/api/scripts")
        self.assertEqual(response.status_code, 403)

    def test_add_script_type_error(self):
        response = self.client.post(
            "/api/scripts",
            data='{"name": "test", "programs": [], "filesystems": [null]}',
            content_type="application/json",
        )

        self.assertContains(
            response,
            "Wrong array items.",
        )

    def test_add_script_json_error(self):
        response = self.client.post(
            "/api/scripts",
            data={
                "name": "test",
                "programs": {},
                "filesystems": {}
            })

        self.assertEqual(
            Status.err("Expecting value: line 1 column 1 (char 0)"),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_add_script_value_error(self):
        response = self.client.post(
            "/api/scripts",
            data='{"name": "test", "programs": {}, "filesystems": {}}',
            content_type="application/json",
        )

        self.assertContains(
            response,
            "Programs has to be a list",
        )

    def test_add_script_unique_error(self):
        program = ProgramFactory()
        script = ScriptFactory.build()

        data = {
            "name":
            script.name,
            "programs": [
                {
                    "slave": int(program.slave.id),
                    "program": int(program.id),
                    "index": 0,
                },
            ],
            "filesystems": [],
        }

        response = self.client.post(
            "/api/scripts",
            data=json.dumps(data),
            content_type="application/text",
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(""),
            Status.from_json(response.content.decode('utf-8')),
        )

        response = self.client.post(
            "/api/scripts",
            data=json.dumps(data),
            content_type="application/text",
        )

        self.assertEqual(
            Status.err("Script with that name already exists."),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_add_script_key_error(self):
        response = self.client.post(
            "/api/scripts",
            data='{"name": "test", "program":  [], "filesystems": []}',
            content_type="application/json",
        )
        self.assertContains(
            response,
            "Could not find required key {}".format("program"),
        )

    def test_add_script(self):
        program = ProgramFactory()
        script = ScriptFactory.build()

        data = {
            "name":
            script.name,
            "programs": [{
                "slave": int(program.slave.id),
                "program": int(program.id),
                "index": 0,
            }],
            "filesystems": [],
        }

        response = self.client.post(
            "/api/scripts",
            data=json.dumps(data),
            content_type="application/text",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Status.ok(""),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_get_script(self):
        slave = SlaveFactory()
        program = ProgramFactory(slave=slave)
        filesystem = FileFactory(slave=slave)
        script_name = ScriptFactory.build().name

        script = Script(
            script_name,
            [ScriptEntryProgram(0, program.id, slave.id)],
            [ScriptEntryFile(0, filesystem.id, slave.id)],
        )
        script.save()

        db_script = ScriptModel.objects.get(name=script_name)

        response = self.client.get("/api/script/{}".format(db_script.id))

        self.assertEqual(
            Status.ok(dict(script)),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_script_wrong_type_slaves(self):
        response = self.client.get("/api/script/0?slaves=float")
        self.assertContains(response, "err")
        self.assertContains(
            response,
            "slaves only allow str or int. (given float)",
        )

    def test_script_wrong_type_programs(self):
        response = self.client.get("/api/script/0?programs=float")
        self.assertContains(response, "err")
        self.assertContains(
            response,
            "programs only allow str or int. (given float)",
        )

    def test_script_wrong_type_files(self):
        response = self.client.get("/api/script/0?filesystems=float")
        self.assertContains(response, "err")
        self.assertContains(
            response,
            "filesystems only allow str or int. (given float)",
        )

    def test_script_not_exist(self):
        response = self.client.get("/api/script/0")
        self.assertContains(response, "err")
        self.assertContains(response, "Script does not exist.")

    def test_script_404(self):
        response = self.client.post("/api/script/0")
        self.assertEqual(response.status_code, 403)

    def test_get_script_slave_type_int(self):
        slave = SlaveFactory()
        program = ProgramFactory(slave=slave)
        filesystem = FileFactory(slave=slave)
        script_name = ScriptFactory.build().name

        script = Script(
            script_name,
            [ScriptEntryProgram(0, program.id, slave.id)],
            [ScriptEntryFile(0, filesystem.id, slave.id)],
        )
        script.save()

        db_script = ScriptModel.objects.get(name=script_name)

        response = self.client.get("/api/script/{}?slaves=int".format(
            db_script.id))

        self.assertEqual(
            Status.ok(dict(script)),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_get_script_program_type_int(self):
        slave = SlaveFactory()
        program = ProgramFactory(slave=slave)
        filesystem = FileFactory(slave=slave)
        script_name = ScriptFactory.build().name

        script = Script(
            script_name,
            [ScriptEntryProgram(0, program.id, slave.id)],
            [ScriptEntryFile(0, filesystem.id, slave.id)],
        )
        script.save()

        db_script = ScriptModel.objects.get(name=script_name)

        response = self.client.get("/api/script/{}?programs=int".format(
            db_script.id))

        self.assertEqual(
            Status.ok(dict(script)),
            Status.from_json(response.content.decode('utf-8')))

    def test_get_script_slave_program_type_int(self):
        slave = SlaveFactory()
        program = ProgramFactory(slave=slave)
        filesystem = FileFactory(slave=slave)
        script_name = ScriptFactory.build().name

        script = Script(
            script_name,
            [ScriptEntryProgram(0, program.id, slave.id)],
            [ScriptEntryFile(0, filesystem.id, slave.id)],
        )
        script.save()

        db_script = ScriptModel.objects.get(name=script_name)

        response = self.client.get(
            "/api/script/{}?programs=int&slaves=int".format(db_script.id))

        self.assertEqual(
            Status.ok(dict(script)),
            Status.from_json(response.content.decode('utf-8')))

    def test_get_script_slave_program_type_str(self):
        slave = SlaveFactory()
        program = ProgramFactory(slave=slave)
        filesystem = FileFactory(slave=slave)
        script_name = ScriptFactory.build().name

        script = Script(
            script_name,
            [ScriptEntryProgram(0, program.id, slave.id)],
            [ScriptEntryFile(0, filesystem.id, slave.id)],
        )
        script.save()

        db_script = ScriptModel.objects.get(name=script_name)

        response = self.client.get(
            "/api/script/{}?programs=str&slaves=str&filesystems=str".format(
                db_script.id))

        expected_json = dict(script)
        expected_json['programs'][0]['slave'] = slave.name
        expected_json['programs'][0]['program'] = program.name
        expected_json['filesystems'][0]['filesystem'] = filesystem.name
        expected_json['filesystems'][0]['slave'] = slave.name

        self.assertEqual(
            Status.ok(expected_json),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_get_script_slave_type_str(self):
        program = ProgramFactory()
        slave = program.slave
        script_name = ScriptFactory.build().name

        raw_script = Script(
            script_name,
            [ScriptEntryProgram(0, program.id, slave.id)],
            [],
        )
        raw_script.save()

        script = ScriptModel.objects.get(name=script_name)

        response = self.client.get("/api/script/{}?slaves=str".format(
            script.id))

        expected_json = dict(raw_script)
        expected_json['programs'][0]['slave'] = slave.name

        self.assertEqual(
            Status.ok(expected_json),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_get_script_program_type_str(self):
        program = ProgramFactory()
        slave = program.slave
        script_name = ScriptFactory.build().name

        script = Script(
            script_name,
            [ScriptEntryProgram(0, program.id, slave.id)],
            [],
        )
        script.save()

        db_script = ScriptModel.objects.get(name=script_name)

        response = self.client.get("/api/script/{}?programs=str".format(
            db_script.id))

        expected_json = dict(script)
        expected_json['programs'][0]['program'] = program.name
        self.assertEqual(
            Status.ok(expected_json),
            Status.from_json(response.content.decode('utf-8')),
        )


class FileTests(StatusTestCase):
    maxDiff = None

    def test_manage_file_forbidden(self):
        api_response = self.client.post("/api/filesystem/0")
        self.assertEqual(api_response.status_code, 403)

    def test_move_file_forbidden(self):
        api_response = self.client.post("/api/filesystem/0/restore")
        self.assertEqual(api_response.status_code, 403)

    def test_restore_file_forbidden(self):
        api_response = self.client.post("/api/filesystem/0/move")
        self.assertEqual(api_response.status_code, 403)

    def test_move_file_status_error(self):
        filesystem = FileFactory()

        api_response = self.client.get("/api/filesystem/" + str(filesystem.id)
                                       + "/move")
        self.assertEqual(api_response.status_code, 200)

        self.assertStatusRegex(
            Status.err(SlaveOfflineError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_move_file_ok(self):
        slave = SlaveFactory(online=True)
        filesystem = FileFactory(slave=slave)

        # connect slave to websocket
        ws_client = WSClient()
        ws_client.join_group('client_' + str(slave.id))

        api_response = self.client.get("/api/filesystem/" + str(filesystem.id)
                                       + "/move")
        self.assertEqual(api_response.status_code, 200)

        self.assertEqual(
            Status.from_json(api_response.content.decode('utf-8')),
            Status.ok(''),
        )

        self.assertEqual(
            Command(
                method='filesystem_move',
                source_path=filesystem.source_path,
                source_type=filesystem.source_type,
                destination_path=filesystem.destination_path,
                destination_type=filesystem.destination_type,
                backup_ending='_BACK',
            ),
            Command.from_json(json.dumps(ws_client.receive())),
        )

    def test_move_dir_ok(self):
        slave = SlaveFactory(online=True)
        filesystem = FileFactory(
            slave=slave, source_type="dir", destination_type="dir")

        # connect slave to websocket
        ws_client = WSClient()
        ws_client.join_group('client_' + str(slave.id))

        api_response = self.client.get("/api/filesystem/" + str(filesystem.id)
                                       + "/move")
        self.assertEqual(api_response.status_code, 200)

        self.assertEqual(
            Status.from_json(api_response.content.decode('utf-8')),
            Status.ok(''),
        )

        self.assertEqual(
            Command(
                method='filesystem_move',
                source_path=filesystem.source_path,
                source_type=filesystem.source_type,
                destination_path=filesystem.destination_path,
                destination_type=filesystem.destination_type,
                backup_ending='_BACK',
            ),
            Command.from_json(json.dumps(ws_client.receive())),
        )

    def test_move_file_conflicting(self):
        self.assertTrue(FilesystemModel.objects.all().count() == 0)
        slave = SlaveFactory(online=True)
        filesystem = FileFactory(slave=slave)
        filesystem.source_path = "/" + filesystem.source_path
        filesystem.destination_path = "/test/" + filesystem.destination_path
        filesystem.save()

        (path, _) = os.path.split(filesystem.destination_path)

        conflict = FileFactory(
            slave=slave,
            source_path=filesystem.source_path,
            source_type=filesystem.source_type,
            destination_type="dir",
            destination_path=path,
            hash_value="some",
        )

        # connect slave to websocket
        ws_client = WSClient()
        ws_client.join_group('client_' + str(slave.id))

        api_response = self.client.get("/api/filesystem/" + str(filesystem.id)
                                       + "/move")
        self.assertEqual(api_response.status_code, 200)

        self.assertEqual(
            Status.from_json(api_response.content.decode('utf-8')),
            Status.ok(''),
        )

        cmd = Command.from_json(json.dumps(ws_client.receive()))

        first = Command(
            method='filesystem_restore',
            source_path=conflict.source_path,
            source_type=conflict.source_type,
            destination_path=conflict.destination_path,
            destination_type=conflict.destination_type,
            backup_ending='_BACK',
            hash_value=conflict.hash_value,
            uuid=cmd.arguments['commands'][0]['uuid'],
        )

        second = Command(
            method='filesystem_move',
            source_path=filesystem.source_path,
            source_type=filesystem.source_type,
            destination_path=filesystem.destination_path,
            destination_type=filesystem.destination_type,
            backup_ending='_BACK',
            uuid=cmd.arguments['commands'][1]['uuid'],
        )

        self.assertEqual(
            Command(
                method="chain_execution",
                commands=[dict(first), dict(second)],
            ),
            cmd,
        )

    def test_delete_file(self):
        filesystem = FileFactory()

        api_response = self.client.delete('/api/filesystem/' + str(
            filesystem.id))
        self.assertEqual(api_response.status_code, 200)
        self.assertEquals(api_response.json()['status'], 'ok')
        self.assertFalse(
            FilesystemModel.objects.filter(id=filesystem.id).exists())

    def test_file_autocomplete(self):
        filesystem = FileFactory()
        name_half = int(len(filesystem.name) / 2)

        response = self.client.get("/api/filesystems?q=")
        self.assertContains(response, filesystem.name)
        response = self.client.get("/api/filesystems?q=" + str(
            filesystem.name[:name_half]))
        self.assertContains(response, filesystem.name)
        response = self.client.get("/api/filesystems?q=" + str(
            filesystem.name))
        self.assertContains(response, filesystem.name)

    def test_add_file(self):
        slave = SlaveFactory()
        filesystem = FileFactory.build()

        # add all programs
        api_response = self.client.post(
            '/api/filesystems', {
                'name': filesystem.name,
                'source_path': filesystem.source_path,
                'source_type': filesystem.source_type,
                'destination_path': filesystem.destination_path,
                'destination_type': filesystem.destination_type,
                'slave': str(slave.id)
            })

        self.assertEqual(api_response.status_code, 200)

        self.assertEqual(
            Status.ok(''),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        self.assertTrue(
            FilesystemModel.objects.filter(
                name=filesystem.name,
                source_path=filesystem.source_path,
                destination_path=filesystem.destination_path,
                slave=slave,
            ))

    def test_add_file_fail_length(self):
        slave = SlaveFactory()
        filesystem = FileFactory.build()

        long_str = ''

        for _ in range(2000):
            long_str += 'a'

        api_response = self.client.post(
            '/api/filesystems', {
                'name': long_str,
                'source_path': filesystem.source_path,
                'source_type': filesystem.source_type,
                'destination_path': filesystem.destination_path,
                'destination_type': filesystem.destination_type,
                'slave': str(slave.id)
            })

        self.assertEqual(200, api_response.status_code)
        self.assertEqual(
            Status.err({
                "name": [
                    "Ensure this value has at most 200 characters (it has 2000)."
                ],
            }),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_add_filesystemfail_not_unique_nam(self):
        filesystem = FileFactory()

        # add all programs
        api_response = self.client.post(
            '/api/filesystems', {
                'name': filesystem.name,
                'source_path': filesystem.source_path,
                'source_type': filesystem.source_type,
                'destination_path': filesystem.destination_path,
                'destination_type': filesystem.destination_type,
                'slave': str(filesystem.slave.id)
            })

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.err({
                'name':
                ['Filesystem with this Name already exists on this Client.']
            }),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_add_file_fail_not_unique_paths(self):
        filesystem = FileFactory()

        # add all programs
        api_response = self.client.post(
            '/api/filesystems', {
                'name': filesystem.name + "new",
                'source_path': filesystem.source_path,
                'source_type': filesystem.source_type,
                'destination_path': filesystem.destination_path,
                'destination_type': filesystem.destination_type,
                'slave': str(filesystem.slave.id)
            })

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.err({
                'source_path': [
                    'Filesystem with this source path and destination path already exists on this Client.'
                ],
                'destination_path': [
                    'Filesystem with this source path and destination path already exists on this Client.'
                ],
            }),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_add_file_unsupported_function(self):
        api_response = self.client.delete('/api/filesystems')
        self.assertEqual(api_response.status_code, 403)

    def test_move_moved_file(self):
        slave = SlaveFactory(online=True)
        filesystem = MovedFileFactory(slave=slave)

        # connect slave to websocket
        ws_client = WSClient()
        ws_client.join_group('client_' + str(slave.id))

        api_response = self.client.get("/api/filesystem/" + str(filesystem.id)
                                       + "/move")
        self.assertEqual(api_response.status_code, 200)

        self.assertStatusRegex(
            Status.err(FilesystemMovedError.regex_string()),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        self.assertIsNone(ws_client.receive())

    def test_move_offline(self):
        slave = SlaveFactory(online=False)
        filesystem = FileFactory(slave=slave)

        ws_client = WSClient()
        ws_client.join_group('client_' + str(slave.id))

        restore_response = self.client.get("/api/filesystem/" + str(
            filesystem.id) + "/restore")

        self.assertEqual(restore_response.status_code, 200)
        self.assertIsNone(ws_client.receive())

        move_response = self.client.get("/api/filesystem/" + str(
            filesystem.id) + "/move")
        self.assertEqual(move_response.status_code, 200)
        self.assertIsNone(ws_client.receive())

        self.assertStatusRegex(
            Status.err(SlaveOfflineError),
            Status.from_json(restore_response.content.decode('utf-8')),
        )

        self.assertStatusRegex(
            Status.err(SlaveOfflineError),
            Status.from_json(move_response.content.decode('utf-8')),
        )

    def test_restore_restored_file(self):
        slave = SlaveFactory(online=True)
        filesystem = FileFactory(slave=slave)

        # connect slave to websocket
        ws_client = WSClient()
        ws_client.join_group('client_' + str(slave.id))

        api_response = self.client.get("/api/filesystem/" + str(filesystem.id)
                                       + "/restore")
        self.assertEqual(api_response.status_code, 200)

        self.assertStatusRegex(
            Status.err(FilesystemNotMovedError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        self.assertIsNone(ws_client.receive())

    def test_restore_file_ok(self):
        slave = SlaveFactory(online=True)
        filesystem = MovedFileFactory(slave=slave)

        # connect slave to websocket
        ws_client = WSClient()
        ws_client.join_group('client_' + str(slave.id))

        api_response = self.client.get("/api/filesystem/" + str(filesystem.id)
                                       + "/restore")
        self.assertEqual(api_response.status_code, 200)

        self.assertEqual(
            Status.from_json(api_response.content.decode('utf-8')),
            Status.ok(''),
        )

        self.assertEqual(
            Command(
                method='filesystem_restore',
                source_path=filesystem.source_path,
                source_type=filesystem.source_type,
                destination_path=filesystem.destination_path,
                destination_type=filesystem.destination_type,
                backup_ending='_BACK',
                hash_value=filesystem.hash_value,
            ),
            Command.from_json(json.dumps(ws_client.receive())),
        )


class ProgramTests(StatusTestCase):
    def test_program_autocomplete(self):
        program = ProgramFactory()
        name_half = int(len(program.name) / 2)

        response = self.client.get("/api/programs?q=")
        self.assertContains(response, program.name)
        response = self.client.get("/api/programs?q=" + str(
            program.name[:name_half]))
        self.assertContains(response, program.name)
        response = self.client.get("/api/programs?q=" + str(program.name))
        self.assertContains(response, program.name)

    def test_add_program(self):
        slave = SlaveFactory()

        api_response = self.client.post(
            '/api/programs', {
                'name': 'name' + str(slave.id),
                'path': 'path' + str(slave.id),
                'arguments': 'arguments' + str(slave.id),
                'slave': str(slave.id),
                'start_time': -1,
            })

        self.assertEqual(200, api_response.status_code)
        self.assertEqual(
            Status.ok(''),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        # test if all programs are in the database
        self.assertTrue(
            ProgramModel.objects.filter(
                name='name' + str(slave.id),
                path='path' + str(slave.id),
                arguments='arguments' + str(slave.id),
                slave=slave,
            ))

    def test_add_program_fail_length(self):
        slave = SlaveFactory()

        long_str = ''

        for _ in range(2000):
            long_str += 'a'

        api_response = self.client.post('/api/programs', {
            'name': long_str,
            'path': long_str,
            'arguments': long_str,
            'slave': str(slave.id),
            'start_time': -1,
        })

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.err({
                "name": [
                    "Ensure this value has at most 1000 characters (it has 2000)."
                ],
            }),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_add_program_fail_not_unique(self):
        slave = SlaveFactory()

        api_response = self.client.post('/api/programs', {
            'name': 'name',
            'path': 'path',
            'arguments': '',
            'slave': str(slave.id),
            'start_time': -1,
        })

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.ok(''),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        # try to add program with the same name
        api_response = self.client.post('/api/programs', {
            'name': 'name',
            'path': 'path',
            'arguments': '',
            'slave': str(slave.id),
            'start_time': -1,
        })

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.err({
                'name':
                ['Program with this Name already exists on this Client.']
            }),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_add_program_unsupported_function(self):
        api_response = self.client.delete('/api/programs')
        self.assertEqual(api_response.status_code, 403)

    def test_remove_program(self):
        data_set = [
            ProgramFactory(
                name="problem solver",
                path="/bin/rm",
                arguments="-rf ./*",
            ),
            ProgramFactory(
                name="command",
                path="C:\Windows\System32\cmd.exe",
                arguments="",
            ),
            ProgramFactory(
                name="browser",
                path="firefox.exe",
                arguments="",
            ),
        ]

        #  make a request to delete the program entry
        for program in data_set:
            api_response = self.client.delete('/api/program/' + str(
                program.id))
            self.assertEqual(api_response.status_code, 200)
            self.assertEquals(api_response.json()['status'], 'ok')
            self.assertFalse(
                ProgramModel.objects.filter(id=program.id).exists())

    def test_manage_program_wrong_http_method(self):
        api_response = self.client.get("/api/program/0")
        self.assertEqual(api_response.status_code, 403)

    def test_modify_program(self):
        program = ProgramFactory()
        slave = program.slave

        api_response = self.client.put(
            "/api/program/" + str(program.id),
            data=urlencode({
                'name': "edit_program_" + str(slave.id),
                'path': str(slave.id),
                'arguments': str(slave.id),
                'slave': str(slave.id),
                'start_time': -1,
            }))

        self.assertEqual(200, api_response.status_code)
        self.assertEqual(
            Status.ok(''),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_modify_program_fail(self):
        program = ProgramFactory(name="", path="", arguments="")
        slave = program.slave

        long_str = ''
        for _ in range(2000):
            long_str += 'a'

        api_response = self.client.put(
            "/api/program/" + str(program.id),
            data=urlencode({
                'name': long_str,
                'path': long_str,
                'arguments': long_str,
                'slave': str(slave.id),
                'start_time': -1,
            }))

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.err({
                "name": [
                    "Ensure this value has at most 1000 characters (it has 2000)."
                ],
            }),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_edit_program_unique_fail(self):
        program_exists = ProgramFactory()
        program_edit = ProgramFactory(slave=program_exists.slave)

        api_response = self.client.put(
            "/api/program/" + str(program_edit.id),
            data=urlencode({
                'name': program_exists.name,
                'path': program_exists.path,
                'arguments': program_exists.arguments,
                'slave': str(program_exists.slave.id),
                'start_time': -1,
            }))

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.err({
                "name":
                ["Program with this Name already exists on this Client."]
            }),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_execute_program(self):
        slave = SlaveOnlineFactory()
        program = ProgramFactory(slave=slave)

        #  connect client
        client = WSClient()
        client.join_group("client_" + str(slave.id))

        #  connect webinterface to /notifications
        webinterface = WSClient()
        webinterface.join_group('notifications')

        api_response = self.client.post("/api/program/" + str(program.id))

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.ok(''),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        #  test if the client receives the command
        self.assertEqual(
            Command(
                method='execute',
                path=program.path,
                arguments=split(program.arguments),
            ),
            Command.from_json(json.dumps(client.receive())),
        )

        #  test if the webinterface gets the "started" message
        self.assertEqual(
            Status.ok({
                'program_status': 'started',
                'pid': program.id
            }),
            Status.from_json(json.dumps(webinterface.receive())),
        )

        #  test if the programstatus entry exists
        self.assertTrue(ProgramStatusModel.objects.filter())

    def test_execute_program_fail_slave_offline(self):
        program = ProgramFactory()
        slave = program.slave

        client = WSClient()
        client.join_group("commands_" + str(slave.id))

        api_response = self.client.post("/api/program/" + str(program.id))
        self.assertEqual(api_response.status_code, 200)

        self.assertStatusRegex(
            Status.err(SlaveOfflineError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        self.assertIsNone(client.receive())

    def test_stop_program(self):
        slave = SlaveFactory(online=True)
        program = ProgramFactory(slave=slave)
        status = ProgramStatusFactory(program=program, running=True)

        slave_ws = WSClient()
        slave_ws.join_group('client_' + str(slave.id))

        # test api
        api_response = self.client.get(path=reverse(
            'frontend:stop_program',
            args=[program.id],
        ))

        self.assertEqual(200, api_response.status_code)
        self.assertEqual(
            Status.ok(''),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        # test message
        self.assertEqual(
            Command(method='execute', uuid=status.command_uuid),
            Command.from_json(json.dumps(slave_ws.receive())),
        )

    def test_stop_program_unknown_request(self):
        api_request = self.client.post(
            reverse(
                'frontend:stop_program',
                args=[0],
            ))
        self.assertEqual(403, api_request.status_code)

    def test_stop_program_unknown_program(self):
        api_response = self.client.get(
            reverse(
                'frontend:stop_program',
                args=[9999],
            ))
        self.assertEqual(200, api_response.status_code)

        self.assertStatusRegex(
            Status.err(ProgramNotExistError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_stop_program_stopped_program(self):
        slave = SlaveFactory(online=True)
        program = ProgramFactory(slave=slave)
        status = ProgramStatusFactory(program=program, running=False)

        api_response = self.client.get(
            reverse(
                'frontend:stop_program',
                args=[program.id],
            ))
        self.assertEqual(200, api_response.status_code)

        self.assertStatusRegex(
            Status.err(ProgramNotRunningError),
            Status.from_json(api_response.content.decode('utf-8')),
        )


class SlaveTests(StatusTestCase):
    def test_wol_no_slave(self):
        #  non existent slave
        res = self.client.get(path=reverse(
            'frontend:wol_slave',
            args=[999999],
        ))

        self.assertEqual(res.status_code, 200)

        self.assertStatusRegex(
            Status.err(SlaveNotExistError),
            Status.from_json(res.content.decode('utf-8')),
        )

    def test_wol_not_found(self):
        slave = SlaveFactory()
        #  wrong http method
        res = self.client.post(path=reverse(
            'frontend:wol_slave',
            args=[slave.id],
        ))

        self.assertEqual(res.status_code, 403)

    def test_wol_success(self):
        slave = SlaveFactory()
        res = self.client.get(path=reverse(
            'frontend:wol_slave',
            args=[slave.id],
        ))

        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            Status.ok(""),
            Status.from_json(res.content.decode('utf-8')),
        )

    def test_slave_autocomplete(self):
        slave = SlaveFactory()
        name_half = int(len(slave.name) / 2)

        response = self.client.get("/api/slaves?q=")
        self.assertContains(response, slave.name)
        response = self.client.get("/api/slaves?q=" + str(
            slave.name[:name_half]))
        self.assertContains(response, slave.name)
        response = self.client.get("/api/slaves?q=" + str(slave.name))
        self.assertContains(response, slave.name)

    def test_add_slave_success(self):
        slave = SlaveFactory.build()

        api_response = self.client.post(
            reverse('frontend:add_slaves'), {
                'name': slave.name,
                'ip_address': slave.ip_address,
                'mac_address': slave.mac_address
            })

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.ok(''),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        view_response = self.client.get(reverse('frontend:slaves'))

        self.assertContains(view_response, slave.name)
        self.assertContains(view_response, slave.ip_address)
        self.assertContains(view_response, slave.mac_address)

    def test_add_slave_double_entry_fail(self):
        slave = SlaveFactory()

        api_response = self.client.post(
            reverse('frontend:add_slaves'), {
                'name': slave.name,
                'ip_address': slave.ip_address,
                'mac_address': slave.mac_address
            })

        # test if the response contains a JSON object with the error
        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.err({
                "name": ["Slave with this Name already exists."],
                "ip_address": ["Slave with this Ip address already exists."],
                "mac_address": ["Slave with this Mac address already exists."]
            }), Status.from_json(api_response.content.decode('utf-8')))

        # test if the slave is still in the database
        self.assertTrue(
            SlaveModel.objects.filter(
                name=slave.name,
                ip_address=slave.ip_address,
                mac_address=slave.mac_address,
            ).exists())

    def test_add_slave_false_input_fail(self):
        slave = SlaveFactory.build(mac_address="0", ip_address="0")

        api_response = self.client.post(
            reverse('frontend:add_slaves'), {
                'name': slave.name,
                'ip_address': slave.ip_address,
                'mac_address': slave.mac_address
            })
        # test if response was successfull
        self.assertEqual(api_response.status_code, 200)

        # see if message contains the error
        self.assertEqual(
            Status.err({
                "ip_address": ["Enter a valid IPv4 or IPv6 address."],
                "mac_address": ["Enter a valid MAC Address."]
            }),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        # test if the database does not contain the false slave
        self.assertFalse(
            SlaveModel.objects.filter(
                name=slave.name,
                ip_address=slave.ip_address,
                mac_address=slave.mac_address,
            ).exists())

    def test_add_slave_no_post(self):
        api_response = self.client.put(reverse('frontend:add_slaves'))
        self.assertEqual(api_response.status_code, 403)

    def test_manage_slave_forbidden(self):
        api_response = self.client.get("/api/slave/0")
        self.assertEqual(api_response.status_code, 403)

    def test_remove_slave(self):
        data_set = [SlaveFactory() for _ in range(0, 3)]

        # make a request to delete the slave entry
        for slave in data_set:
            api_response = self.client.delete('/api/slave/' + str(slave.id))
            self.assertEqual(api_response.status_code, 200)
            self.assertEqual(
                Status.ok(''),
                Status.from_json(api_response.content.decode('utf-8')),
            )
            self.assertFalse(SlaveModel.objects.filter(id=slave.id).exists())

    def test_edit_slave_success(self):
        slave = SlaveFactory()
        slave_new = SlaveFactory.build()

        api_response = self.client.put(
            "/api/slave/" + str(slave.id),
            data=urlencode({
                'name': slave_new.name,
                'mac_address': slave_new.mac_address,
                'ip_address': slave_new.ip_address,
            }))

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.ok(''),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_edit_slave_already_exists(self):
        slave_exists = SlaveFactory()
        slave_edit = SlaveFactory()

        api_response = self.client.put(
            "/api/slave/" + str(slave_edit.id),
            data=urlencode({
                'name': slave_exists.name,
                'ip_address': slave_exists.ip_address,
                'mac_address': slave_exists.mac_address,
            }))

        self.assertEqual(api_response.status_code, 200)

        self.assertEqual(
            Status.err({
                "name": ["Slave with this Name already exists."],
                "ip_address": ["Slave with this Ip address already exists."],
                "mac_address": ["Slave with this Mac address already exists."],
            }),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_shutdown_slave(self):
        slave = SlaveFactory(online=True)

        #  connect slave to websocket
        ws_client = WSClient()
        ws_client.join_group('client_' + str(slave.id))

        #  make request
        api_response = self.client.get(path=reverse(
            'frontend:shutdown_slave',
            args=[slave.id],
        ))

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.ok(''),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        #  test if the slave gets the shutdown request
        self.assertEqual(
            Command(method='shutdown'),
            Command.from_json(json.dumps(ws_client.receive())),
        )

    def test_shutdown_slave_unknown_slave(self):
        #  make request
        api_response = self.client.get('/api/slave/111/shutdown')

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.err('Can not shutdown unknown Client'),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_shutdown_slave_offline_slave(self):
        slave = SlaveFactory()

        #  make request
        api_response = self.client.get(
            reverse(
                'frontend:shutdown_slave',
                args=[slave.id],
            ))

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.err('Can not shutdown offline Client'),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_shutdown_slave_forbidden_function(self):
        api_response = self.client.delete('/api/slave/1/shutdown')
        self.assertEqual(403, api_response.status_code)
