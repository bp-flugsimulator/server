"""
TESTCASES NAMEING SCHEME

def test_<API>_<HTTP METHOD>_<LIST>:
  pass

<API>:
    the name of handler method without the type information (e.g. filesystem_set -> set)

<HTTP METHOD>:
    The used http method in the test function

 <LIST>:
    forbidden -> method not allowed
    not_exist -> the addressed object does not exist
    offline   -> the slave is offline
    success   -> example successfull request
    exist     -> the request is not successfull because something exists or is running
"""
#  pylint: disable=C0111,C0103

import json
import os

from urllib.parse import urlencode
from shlex import split

from django.test import TestCase
from django.urls import reverse
from channels.test import WSClient

from utils import Status, Command

from frontend.scripts import Script, ScriptEntryFilesystem, ScriptEntryProgram

from frontend.models import (
    Script as ScriptModel,
    ScriptGraphPrograms as SGP,
    ScriptGraphFiles as SGF,
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
    FilesystemNotExistError,
    FilesystemDeleteError,
    SimultaneousQueryError,
    LogNotExistError,
    ScriptNotExistError,
    QueryTypeError,
)

from .factory import (
    SlaveFactory,
    SlaveOnlineFactory,
    ProgramFactory,
    ScriptFactory,
    SGFFactory,
    SGPFactory,
    FileFactory,
    MovedFileFactory,
    ProgramStatusFactory,
)

from .testcases import StatusTestCase
"""
"""


class ScriptTest(StatusTestCase):
    def test_run_put_forbidden(self):
        response = self.client.put(reverse("frontend:script_run", args=[0]))
        self.assertEqual(response.status_code, 403)

    def test_run_get_not_exist(self):
        response = self.client.get(reverse("frontend:script_run", args=[0]))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(ScriptNotExistError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_delete_success(self):
        slave = SlaveFactory()
        program = ProgramFactory(slave=slave)
        filesystem = FileFactory(slave=slave)
        script_name = ScriptFactory.build().name

        script = Script(
            script_name,
            [ScriptEntryProgram(0, program.name, slave.name)],
            [ScriptEntryFilesystem(0, filesystem.name, slave.name)],
        )
        script.save()

        db_script = ScriptModel.objects.get(name=script_name)

        response = self.client.delete(reverse("frontend:script_entry",
                                              args=[db_script.id]),)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ScriptModel.objects.filter(name=script_name).exists())

    def test_set_put_forbidden(self):
        response = self.client.put(reverse("frontend:script_set"))
        self.assertEqual(response.status_code, 403)

    def test_set_post_type_error(self):
        #TODO: fix this test
        response = self.client.post(
            reverse("frontend:script_set"),
            data='{"name": "test", "programs": [], "filesystems": [null]}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "All elements in filesystems has to be dict.",
        )

        self.assertContains(
            response,
            "0 has type NoneType",
        )

    def test_set_post_value_error(self):
        response = self.client.post(
            reverse("frontend:script_set"),
            data={
                "name": "test",
                "programs": {},
                "filesystems": {}
            })
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.err("Expecting value: line 1 column 1 (char 0)"),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_set_post_success(self):
        #TODO: fix this test
        response = self.client.post(
            reverse("frontend:script_set"),
            data='{"name": "test", "programs": {}, "filesystems": {}}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "programs has to be list",
        )

    def test_set_post_unique_error(self):
        program = ProgramFactory()
        script = ScriptFactory.build()

        data = {
            "name":
            script.name,
            "programs": [
                {
                    "slave": program.slave.id,
                    "program": program.id,
                    "index": 0,
                },
            ],
            "filesystems": [],
        }

        response = self.client.post(
            reverse("frontend:script_set"),
            data=json.dumps(data),
            content_type="application/text",
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(""),
            Status.from_json(response.content.decode('utf-8')),
        )

        response = self.client.post(
            reverse("frontend:script_set"),
            data=json.dumps(data),
            content_type="application/text",
        )

        self.assertEqual(
            Status.err("Script with this Name already exists."),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_set_post_key_error(self):
        response = self.client.post(
            reverse("frontend:script_set"),
            data='{"name": "test", "program":  [], "filesystems": []}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "Could not find required key {}".format("program"),
        )

    def test_set_post_success(self):
        program = ProgramFactory()
        script = ScriptFactory.build()

        data = {
            "name":
            script.name,
            "programs": [{
                "slave": program.slave.id,
                "program": program.id,
                "index": 0,
            }],
            "filesystems": [],
        }

        response = self.client.post(
            reverse("frontend:script_set"),
            data=json.dumps(data),
            content_type="application/text",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Status.ok(""),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_get_success(self):
        slave = SlaveFactory()
        program = ProgramFactory(slave=slave)
        filesystem = FileFactory(slave=slave)
        script_name = ScriptFactory.build().name

        script = Script(
            script_name,
            [ScriptEntryProgram(0, program.id, slave.id)],
            [ScriptEntryFilesystem(0, filesystem.id, slave.id)],
        )
        script.save()

        db_script = ScriptModel.objects.get(name=script_name)

        response = self.client.get(
            reverse("frontend:script_entry", args=[db_script.id]),
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(dict(script)),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_get_type_error(self):
        response = self.client.get(
            reverse("frontend:script_entry", args=[0]),
            {'slaves': 'float'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(ScriptNotExistError),
            Status.from_json(response.content.decode('utf-8')),
        )

        response = self.client.get(
            reverse("frontend:script_entry", args=[0]),
            {'programs': 'float'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(ScriptNotExistError),
            Status.from_json(response.content.decode('utf-8')),
        )

        response = self.client.get(
            reverse("frontend:script_entry", args=[0]),
            {'filesystems': 'float'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(ScriptNotExistError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_get_not_exist(self):
        response = self.client.get(reverse("frontend:script_entry", args=[0]))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(ScriptNotExistError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_post_forbidden(self):
        response = self.client.post(reverse("frontend:script_entry", args=[0]))
        self.assertEqual(response.status_code, 403)

    def test_entry_get_query_slaves_success(self):
        slave = SlaveFactory()
        program = ProgramFactory(slave=slave)
        filesystem = FileFactory(slave=slave)
        script_name = ScriptFactory.build().name

        script_int = Script(
            script_name,
            [ScriptEntryProgram(0, program.id, slave.id)],
            [ScriptEntryFilesystem(0, filesystem.id, slave.id)],
        )
        script_int.save()

        script_str = Script(
            script_name,
            [ScriptEntryProgram(0, program.id, slave.name)],
            [ScriptEntryFilesystem(0, filesystem.id, slave.name)],
        )

        db_script = ScriptModel.objects.get(name=script_name)

        response = self.client.get(
            reverse("frontend:script_entry", args=[db_script.id],),
            {'slaves': 'int'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(dict(script_int)),
            Status.from_json(response.content.decode('utf-8')),
        )

        response = self.client.get(
            reverse("frontend:script_entry", args=[db_script.id],),
            {'slaves': 'str'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(dict(script_str)),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_get_query_programs_success(self):
        slave = SlaveFactory()
        program = ProgramFactory(slave=slave)
        filesystem = FileFactory(slave=slave)
        script_name = ScriptFactory.build().name

        script_int = Script(
            script_name,
            [ScriptEntryProgram(0, program.id, slave.id)],
            [ScriptEntryFilesystem(0, filesystem.id, slave.id)],
        )
        script_int.save()

        script_str = Script(
            script_name,
            [ScriptEntryProgram(0, program.name, slave.id)],
            [ScriptEntryFilesystem(0, filesystem.id, slave.id)],
        )

        db_script = ScriptModel.objects.get(name=script_name)

        response = self.client.get(
            reverse("frontend:script_entry", args=[db_script.id],),
            {'programs': 'int'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(dict(script_int)),
            Status.from_json(response.content.decode('utf-8')),
        )

        response = self.client.get(
            reverse("frontend:script_entry", args=[db_script.id],),
            {'programs': 'str'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(dict(script_str)),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_get_query_filesystem_success(self):
        slave = SlaveFactory()
        program = ProgramFactory(slave=slave)
        filesystem = FileFactory(slave=slave)
        script_name = ScriptFactory.build().name

        script_int = Script(
            script_name,
            [ScriptEntryProgram(0, program.id, slave.id)],
            [ScriptEntryFilesystem(0, filesystem.id, slave.id)],
        )
        script_int.save()

        script_str = Script(
            script_name,
            [ScriptEntryProgram(0, program.id, slave.id)],
            [ScriptEntryFilesystem(0, filesystem.name, slave.id)],
        )

        db_script = ScriptModel.objects.get(name=script_name)

        response = self.client.get(
            reverse("frontend:script_entry", args=[db_script.id],),
            {'filesystems': 'int'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(dict(script_int)),
            Status.from_json(response.content.decode('utf-8')),
        )

        response = self.client.get(
            reverse("frontend:script_entry", args=[db_script.id],),
            {'filesystems': 'str'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(dict(script_str)),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_copy_get_success(self):
        script = ScriptFactory()
        sgp = SGPFactory(script=script)
        sgf = SGFFactory(script=script)

        resp = self.client.get(
            reverse('frontend:script_copy', args=[str(script.id)]))

        self.assertEqual(
            Status.ok(''),
            Status.from_json(resp.content.decode('utf-8')),
        )
        self.assertTrue(
            ScriptModel.objects.filter(name=script.name + '_copy').exists())

        self.assertTrue(SGF.objects.filter(script=script).exists())
        sgf_copy = SGF.objects.get(script=script)
        self.assertEqual(sgf.index, sgf_copy.index)
        self.assertEqual(sgf.filesystem, sgf_copy.filesystem)

        self.assertTrue(SGP.objects.filter(script=script).exists())
        sgp_copy = SGP.objects.get(script=script)
        self.assertEqual(sgp.index, sgp_copy.index)
        self.assertEqual(sgp.program, sgp_copy.program)

        for i in range(1, 10):
            resp = self.client.get(
                reverse('frontend:script_copy', args=[script.id]))
            self.assertEqual(
                Status.ok(''),
                Status.from_json(resp.content.decode('utf-8')),
            )
            copy_name = "{}_copy_{}".format(script.name, i)
            self.assertTrue(ScriptModel.objects.filter(name=copy_name).exists())

    def test_copy_get_not_exist(self):
        resp = self.client.get(reverse(
            'frontend:script_copy',
            args=[0],
        ))

        self.assertStatusRegex(
            Status.err(ScriptNotExistError),
            Status.from_json(resp.content.decode('utf-8')),
        )

    def test_copy_delete_forbidden(self):
        api_response = self.client.delete(
            reverse('frontend:script_copy', args=['0']))
        self.assertEqual(403, api_response.status_code)

    def test_entry_put_success(self):
        # send the same object to the api route
        script = ScriptFactory()
        SGPFactory(script=script)
        SGFFactory(script=script)
        script_script = Script.from_model(script.id, "str", "str", "str")

        api_response = self.client.put(
            reverse("frontend:script_entry", args=[script.id]),
            data=json.dumps(dict(script_script)),
        )

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.ok(""),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        # modifiy the element and resend it
        slave2 = SlaveFactory()
        filesystem2 = FileFactory(slave=slave2)
        sgf2 = SGFFactory.build(script=script, filesystem=filesystem2)

        script_script.filesystems.append(
            ScriptEntryFilesystem(sgf2.index, sgf2.filesystem.name,
                                  sgf2.filesystem.slave.name,),
        )

        api_response = self.client.put(
            reverse("frontend:script_entry", args=[script.id]),
            data=json.dumps(dict(script_script)),
        )

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.ok(""),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        new_script_script = Script.from_model(script.id, "str", "str", "str")
        self.assertEqual(script_script, new_script_script)

    def test_entry_put_exist(self):
        script = ScriptFactory()
        script2 = ScriptFactory()
        SGPFactory(script=script)
        SGFFactory(script=script)

        script_script = Script.from_model(script.id, "str", "str", "str")

        script_script.name = script2.name
        api_response = self.client.put(
            reverse("frontend:script_entry", args=[script.id]),
            data=json.dumps(dict(script_script)),
        )

        self.assertEqual(api_response.status_code, 200)
        self.assertContains(api_response, "UNIQUE constraint failed")


class FilesystemTests(StatusTestCase):
    maxDiff = None

    def test_manage_file_forbidden(self):
        api_response = self.client.post("/api/filesystem/0")
        self.assertEqual(api_response.status_code, 403)

    def test_delete_moved_error(self):
        filesystem = FileFactory(hash_value="Some")
        api_response = self.client.delete(
            "/api/filesystem/" + str(filesystem.id))
        self.assertEqual(api_response.status_code, 200)

        self.assertStatusRegex(
            Status.err(FilesystemDeleteError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_move_file_forbidden(self):
        api_response = self.client.post("/api/filesystem/0/restore")
        self.assertEqual(api_response.status_code, 403)

    def test_restore_file_forbidden(self):
        api_response = self.client.post("/api/filesystem/0/move")
        self.assertEqual(api_response.status_code, 403)

    def test_move_file_status_error(self):
        filesystem = FileFactory()

        api_response = self.client.get(
            "/api/filesystem/" + str(filesystem.id) + "/move")
        self.assertEqual(api_response.status_code, 200)

        self.assertStatusRegex(
            Status.err(SlaveOfflineError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_move_get_not_exist(self):
        api_response = self.client.get("/api/filesystem/" + str(0) + "/move")

        self.assertEqual(api_response.status_code, 200)

        self.assertStatusRegex(
            Status.err(FilesystemNotExistError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_restore_get_not_exist(self):
        api_response = self.client.get(
            "/api/filesystem/" + str(0) + "/restore")

        self.assertEqual(api_response.status_code, 200)

        self.assertStatusRegex(
            Status.err(FilesystemNotExistError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_entry_delete_not_exist(self):
        api_response = self.client.delete("/api/filesystem/" + str(0))

        self.assertEqual(api_response.status_code, 200)

        self.assertStatusRegex(
            Status.err(FilesystemNotExistError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_move_file_ok(self):
        slave = SlaveFactory(online=True)
        filesystem = FileFactory(slave=slave)

        # connect slave to websocket
        ws_client = WSClient()
        ws_client.join_group('client_' + str(slave.id))

        api_response = self.client.get(
            "/api/filesystem/" + str(filesystem.id) + "/move")
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

        api_response = self.client.get(
            "/api/filesystem/" + str(filesystem.id) + "/move")
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

        api_response = self.client.get(
            "/api/filesystem/" + str(filesystem.id) + "/move")
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

        api_response = self.client.delete(
            '/api/filesystem/' + str(filesystem.id))
        self.assertEqual(api_response.status_code, 200)
        self.assertEquals(api_response.json()['status'], 'ok')
        self.assertFalse(
            FilesystemModel.objects.filter(id=filesystem.id).exists())

    def test_file_autocomplete(self):
        filesystem = FileFactory()
        name_half = int(len(filesystem.name) / 2)

        response = self.client.get("/api/filesystems?q=")
        self.assertContains(response, filesystem.name)
        response = self.client.get(
            "/api/filesystems?q=" + str(filesystem.name[:name_half]))
        self.assertContains(response, filesystem.name)
        response = self.client.get(
            "/api/filesystems?q=" + str(filesystem.name))
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

    def test_query_get_all_by_slave(self):
        filesystem = FileFactory()

        with_str = self.client.get(
            '/api/filesystems?slave={}&slave_str=True'.format(
                filesystem.slave.name))

        whithout_str = self.client.get(
            '/api/filesystems?slave={}&slave_str=False'.format(
                filesystem.slave.id))

        ints = self.client.get('/api/filesystems?slave={}'.format(
            filesystem.slave.id))

        self.assertEqual(with_str.status_code, 200)
        self.assertEqual(whithout_str.status_code, 200)
        self.assertEqual(ints.status_code, 200)

        with_str = Status.from_json(with_str.content.decode('utf-8'))
        ints = Status.from_json(ints.content.decode('utf-8'))
        without_str = Status.from_json(whithout_str.content.decode('utf-8'))

        self.assertEqual(
            ints,
            without_str,
        )

        slaves = FilesystemModel.objects.filter(id=filesystem.id).values_list(
            "name",
            flat=True,
        )
        slaves = list(slaves)

        self.assertEqual(
            with_str,
            Status.ok(slaves),
        )
        self.assertEqual(
            ints,
            Status.ok(slaves),
        )

    def test_query_get_all_wrong_type(self):
        resp = self.client.get('/api/filesystems?slave=not_an_int')

        self.assertEqual(resp.status_code, 200)

        self.assertStatusRegex(
            Status.err(QueryTypeError),
            Status.from_json(resp.content.decode('utf-8')),
        )

    def test_query_get_does_not_exist(self):
        resp_int = self.client.get('/api/filesystems?slave=-1')
        resp_str = self.client.get(
            '/api/filesystems?slave=none&slave_str=True')

        self.assertEqual(resp_int.status_code, 200)
        self.assertEqual(resp_str.status_code, 200)

        self.assertStatusRegex(
            Status.err(SlaveNotExistError),
            Status.from_json(resp_int.content.decode('utf-8')),
        )

        self.assertStatusRegex(
            Status.err(SlaveNotExistError),
            Status.from_json(resp_str.content.decode('utf-8')),
        )

    def test_query_get_all(self):
        resp = self.client.get('/api/filesystems')

        self.assertEqual(resp.status_code, 200)

        self.assertEqual(
            Status.ok([]),
            Status.from_json(resp.content.decode('utf-8')),
        )

        filesystem = FileFactory()

        resp = self.client.get('/api/filesystems')
        self.assertEqual(
            Status.ok([filesystem.name]),
            Status.from_json(resp.content.decode('utf-8')),
        )

    def test_allowed_methods(self):
        self.client.put("/api/filesystem")

    def test_add_file_unsupported_function(self):
        api_response = self.client.delete('/api/filesystems')
        self.assertEqual(api_response.status_code, 403)

    def test_move_moved_file(self):
        slave = SlaveFactory(online=True)
        filesystem = MovedFileFactory(slave=slave)

        # connect slave to websocket
        ws_client = WSClient()
        ws_client.join_group('client_' + str(slave.id))

        api_response = self.client.get(
            "/api/filesystem/" + str(filesystem.id) + "/move")
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

        restore_response = self.client.get(
            "/api/filesystem/" + str(filesystem.id) + "/restore")

        self.assertEqual(restore_response.status_code, 200)
        self.assertIsNone(ws_client.receive())

        move_response = self.client.get(
            "/api/filesystem/" + str(filesystem.id) + "/move")
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

        api_response = self.client.get(
            "/api/filesystem/" + str(filesystem.id) + "/restore")
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

        api_response = self.client.get(
            "/api/filesystem/" + str(filesystem.id) + "/restore")
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

    def test_edit_filesystem_wrong_http_method(self):
        api_response = self.client.get("/api/filesystem/0")
        self.assertEqual(api_response.status_code, 403)

    def test_modify_filesystem(self):
        filesystem = FileFactory()
        slave = filesystem.slave

        api_response = self.client.put(
            "/api/filesystem/" + str(filesystem.id),
            data=urlencode({
                'name': "edit_filesystem_" + str(slave.id),
                'source_path': str(slave.id),
                'destination_path': str(slave.id),
                'slave': str(slave.id),
                'source_type': filesystem.source_type,
                'destination_type': filesystem.destination_type,
            }))

        self.assertEqual(200, api_response.status_code)
        self.assertEqual(
            Status.ok(''),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_modify_filesystem_fail(self):
        filesystem = FileFactory(name="", source_path="", destination_path="")
        slave = filesystem.slave

        long_str = ''
        for _ in range(2000):
            long_str += 'a'

        api_response = self.client.put(
            "/api/filesystem/" + str(filesystem.id),
            data=urlencode({
                'name': long_str,
                'source_path': long_str,
                'destination_path': long_str,
                'slave': str(slave.id),
                'source_type': filesystem.source_type,
                'destination_type': filesystem.destination_type,
            }))

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.err({
                "name": [
                    "Ensure this value has at most 200 characters (it has 2000)."
                ],
            }),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_edit_filesystem_unique_fail(self):
        filesystem_exists = FileFactory()
        filesystem_edit = FileFactory(slave=filesystem_exists.slave)

        api_response = self.client.put(
            "/api/filesystem/" + str(filesystem_edit.id),
            data=urlencode({
                'name':
                filesystem_exists.name,
                'source_path':
                filesystem_exists.source_path,
                'destination_path':
                filesystem_exists.destination_path,
                'slave':
                str(filesystem_exists.slave.id),
                'source_type':
                filesystem_exists.source_type,
                'destination_type':
                filesystem_exists.destination_type,
            }))

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.err({
                "name":
                ["Filesystem with this Name already exists on this Client."]
            }),
            Status.from_json(api_response.content.decode('utf-8')),
        )


class ProgramTests(StatusTestCase):

    def test_entry_get_forbidden(self):
        api_response = self.client.get(reverse('frontend:program_entry', args=[1234]))
        self.assertEqual(api_response.status_code, 403)

    def test_entry_get_offline_slave(self):
        program = ProgramFactory()
        api_response = self.client.get(
            reverse('frontend:log_entry', args=[program.id]))
        self.assertEqual(200, api_response.status_code)
        self.assertStatusRegex(
            Status.err(SlaveOfflineError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_entry_delete_success(self):
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
            api_response = self.client.delete(reverse('frontend:program_entry', args=[program.id]))
            self.assertEqual(api_response.status_code, 200)
            self.assertEquals(api_response.json()['status'], 'ok')
            self.assertFalse(
                ProgramModel.objects.filter(id=program.id).exists())

    def test_entry_put_success(self):
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

    def test_entry_put_not_exist(self):
        api_response = self.client.put(
            reverse('frontend:program_entry', args=['1234']))
        self.assertEqual(200, api_response.status_code)
        self.assertStatusRegex(
            Status.err(ProgramNotExistError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_entry_put_value_error(self):
        program = ProgramFactory(name="", path="", arguments="")
        slave = program.slave

        long_str = ''
        for _ in range(2000):
            long_str += 'a'

        api_response = self.client.put(reverse('frontend:program_entry', args=[program.id]),
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

    def test_entry_put_unique_error(self):
        program_exists = ProgramFactory()
        program_edit = ProgramFactory(slave=program_exists.slave)

        api_response = self.client.put(reverse('frontend:program_entry', args=[program_edit.id]),
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

    def test_set_get_success(self):
        program = ProgramFactory()

        with_str = self.client.get(reverse('frontend:program_set'), {'slave':str(program.slave.name), 'slave_str':True})
        whithout_str = self.client.get(reverse('frontend:program_set'), {'slave': str(program.slave.id), 'slave_str':False})
        ints = self.client.get(reverse('frontend:program_set'), {'slave': str(program.slave.id)})

        with_str = Status.from_json(with_str.content.decode('utf-8'))
        ints = Status.from_json(ints.content.decode('utf-8'))
        without_str = Status.from_json(whithout_str.content.decode('utf-8'))

        self.assertEqual(
            ints,
            without_str,
        )

        slaves = ProgramModel.objects.filter(id=program.id).values_list(
            "name",
            flat=True,
        )
        slaves = list(slaves)

        self.assertEqual(
            with_str,
            Status.ok(slaves),
        )
        self.assertEqual(
            ints,
            Status.ok(slaves),
        )

    def test_set_get_success_query(self):
        program = ProgramFactory()
        name_half = int(len(program.name) / 2)

        response = self.client.get(reverse('frontend:program_set'), {'q':''})
        self.assertEqual(
            Status.ok([program.name]),
            Status.from_json(response.content.decode('utf-8')),
        )

        response = self.client.get(reverse('frontend:program_set'), {'q':str(program.name[:name_half])})
        self.assertEqual(
            Status.ok([program.name]),
            Status.from_json(response.content.decode('utf-8')),
        )
        response = self.client.get(reverse('frontend:program_set'), {'q':str(program.name)})
        self.assertEqual(
            Status.ok([program.name]),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_set_get_success_get_all(self):
        resp = self.client.get(reverse('frontend:program_set'))
        self.assertEqual(
            Status.ok([]),
            Status.from_json(resp.content.decode('utf-8')),
        )

        program = ProgramFactory()

        resp = self.client.get(reverse('frontend:program_set'))
        self.assertEqual(
            Status.ok([program.name]),
            Status.from_json(resp.content.decode('utf-8')),
        )

    def test_set_get_value_error(self):
        resp = self.client.get(reverse('frontend:program_set'), {'slave': 'notanint', 'slave_str':False})

        self.assertEqual(
            Status.err("Slave has to be an integer."),
            Status.from_json(resp.content.decode('utf-8')),
        )

    def test_set_get_not_exist(self):
        resp_int = self.client.get(reverse('frontend:program_set'), {'slave':-1})
        resp_str = self.client.get(reverse('frontend:program_set'), {'slave': None, 'slave_str':True})

        self.assertStatusRegex(
            Status.err(SlaveNotExistError),
            Status.from_json(resp_int.content.decode('utf-8')),
        )

        self.assertStatusRegex(
            Status.err(SlaveNotExistError),
            Status.from_json(resp_str.content.decode('utf-8')),
        )

    def test_set_post_success(self):
        slave = SlaveFactory()
        api_response = self.client.post(
            reverse('frontend:program_set'),
            {
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

    def test_set_post_value_to_long_error(self):
        slave = SlaveFactory()

        long_str = ''

        for _ in range(2000):
            long_str += 'a'

        api_response = self.client.post(
            reverse('frontend:program_set'),
            {
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

    def test_set_post_value_error(self):
        slave = SlaveFactory()

        api_response = self.client.post(reverse('frontend:program_set'), {
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
        api_response = self.client.post(reverse('frontend:program_set'),
            {
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

    def test_set_delete_forbidden(self):
        api_response = self.client.delete(reverse('frontend:program_set'))
        self.assertEqual(api_response.status_code, 403)

    def test_start_get_success(self):
        slave = SlaveOnlineFactory()
        program = ProgramFactory(slave=slave)

        #  connect client
        client = WSClient()
        client.join_group("client_" + str(slave.id))

        #  connect webinterface to /notifications
        webinterface = WSClient()
        webinterface.join_group('notifications')

        api_response = self.client.get(
            reverse('frontend:program_start', args=[program.id]))

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.ok(''),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        #  test if the client receives the command
        cmd = Command.from_json(json.dumps(client.receive()))
        self.assertEqual(
            Command(
                pid=program.id,
                own_uuid=cmd.uuid,
                method='execute',
                path=program.path,
                arguments=split(program.arguments),
            ),
            cmd,
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

    def test_start_post_exist(self):
        slave = SlaveFactory(online=True)
        program = ProgramFactory(slave=slave)
        ProgramStatusFactory(program=program, running=True)

        api_response = self.client.get(
            reverse('frontend:program_start', args=[program.id]))

        self.assertEqual(api_response.status_code, 200)

        self.assertStatusRegex(
            Status.err(ProgramRunningError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_start_forbidden(self):
        api_response = self.client.delete(
            reverse('frontend:program_start', args=['0']))
        self.assertEqual(403, api_response.status_code)

    def test_start_get_not_exist(self):
        api_response = self.client.get(
            reverse('frontend:program_start', args=[1234]))

        self.assertEqual(api_response.status_code, 200)

        self.assertStatusRegex(
            Status.err(ProgramNotExistError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_start_get_offline(self):
        program = ProgramFactory()
        slave = program.slave

        client = WSClient()
        client.join_group("commands_" + str(slave.id))

        api_response = self.client.get(
            reverse('frontend:program_start', args=[program.id]))
        self.assertEqual(api_response.status_code, 200)

        self.assertStatusRegex(
            Status.err(SlaveOfflineError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        self.assertIsNone(client.receive())

    def test_stop_get_offline_error(self):
        slave = SlaveFactory(online=True)
        program = ProgramFactory(slave=slave)
        status = ProgramStatusFactory(program=program, running=True)

        slave_ws = WSClient()
        slave_ws.join_group('client_' + str(slave.id))

        # test api
        api_response = self.client.get(
            path=reverse(
                'frontend:program_stop',
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

    def test_stop_post_forbidden(self):
        api_request = self.client.post(
            reverse(
                'frontend:program_stop',
                args=[0],
            ))
        self.assertEqual(403, api_request.status_code)

    def test_stop_get_not_exist(self):
        api_response = self.client.get(
            reverse(
                'frontend:program_stop',
                args=[9999],
            ))
        self.assertEqual(200, api_response.status_code)

        self.assertStatusRegex(
            Status.err(ProgramNotExistError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_stop_get_not_running_error(self):
        slave = SlaveFactory(online=True)
        program = ProgramFactory(slave=slave)
        ProgramStatusFactory(program=program, running=False)

        api_response = self.client.get(
            reverse(
                'frontend:program_stop',
                args=[program.id],
            ))
        self.assertEqual(200, api_response.status_code)

        self.assertStatusRegex(
            Status.err(ProgramNotRunningError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_stop_get_offline(self):
        program = ProgramFactory()

        api_response = self.client.get(reverse('frontend:program_stop', args=[program.id]))
        self.assertEqual(api_response.status_code, 200)
        self.assertStatusRegex(
            Status.err(SlaveOfflineError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_log_entry_get_success(self):
        slave = SlaveFactory(online=True)
        program = ProgramFactory(slave=slave)
        status = ProgramStatusFactory(running=True, program=program)

        ws_slave = WSClient()
        ws_slave.join_group('client_' + str(slave.id))

        api_response = self.client.get(
            reverse('frontend:log_entry', args=[program.id]))
        self.assertEqual(200, api_response.status_code)
        self.assertEqual(
            Status.ok(''),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        self.assertEqual(
            Command(
                method='get_log',
                target_uuid=status.command_uuid,
            ),
            Command.from_json(json.dumps(ws_slave.receive())),
        )

    def test_log_entry_get_not_exist_log(self):
        slave = SlaveFactory(online=True)
        program = ProgramFactory(slave=slave)
        api_response = self.client.get(
            reverse('frontend:log_entry', args=[program.id]))
        self.assertEqual(200, api_response.status_code)
        self.assertStatusRegex(
            Status.err(LogNotExistError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_log_entry_get_not_exist_program(self):
        api_response = self.client.get(
            reverse('frontend:log_entry', args=[999999]))
        self.assertEqual(200, api_response.status_code)
        self.assertStatusRegex(
            Status.err(ProgramNotExistError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_log_entry_post_forbidden(self):
        api_response = self.client.post(
            reverse('frontend:log_entry', args=[999999]))
        self.assertEqual(403, api_response.status_code)

    def test_log_disable_get_success(self):
        slave = SlaveFactory(online=True)
        program = ProgramFactory(slave=slave)
        status = ProgramStatusFactory(running=True, program=program)

        ws_slave = WSClient()
        ws_slave.join_group('client_' + str(slave.id))

        api_response = self.client.get(
            reverse('frontend:log_disable', args=[program.id]))
        self.assertEqual(200, api_response.status_code)
        self.assertEqual(
            Status.ok(''),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        self.assertEqual(
            Command(
                method='disable_logging',
                target_uuid=status.command_uuid,
            ),
            Command.from_json(json.dumps(ws_slave.receive())),
        )

    def test_log_disable_get_offline(self):
        program = ProgramFactory()
        api_response = self.client.get(
            reverse('frontend:log_disable', args=[program.id]))
        self.assertEqual(200, api_response.status_code)
        self.assertStatusRegex(
            Status.err(SlaveOfflineError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_log_disable_get_not_exist(self):
        api_response = self.client.get(
            reverse('frontend:log_disable', args=[999999]))
        self.assertEqual(200, api_response.status_code)
        self.assertStatusRegex(
            Status.err(ProgramNotExistError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_log_disable_post_forbidden(self):
        api_response = self.client.post(
            reverse('frontend:log_disable', args=[999999]))
        self.assertEqual(403, api_response.status_code)

    def test_log_enable_get_success(self):
        slave = SlaveFactory(online=True)
        program = ProgramFactory(slave=slave)
        status = ProgramStatusFactory(running=True, program=program)

        ws_slave = WSClient()
        ws_slave.join_group('client_' + str(slave.id))

        api_response = self.client.get(
            reverse('frontend:log_enable', args=[program.id]))
        self.assertEqual(200, api_response.status_code)
        self.assertEqual(
            Status.ok(''),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        self.assertEqual(
            Command(
                method='enable_logging',
                target_uuid=status.command_uuid,
            ),
            Command.from_json(json.dumps(ws_slave.receive())),
        )

    def test_log_enable_get_offline_error(self):
        program = ProgramFactory()
        api_response = self.client.get(
            reverse('frontend:log_enable', args=[program.id]))
        self.assertEqual(200, api_response.status_code)
        self.assertStatusRegex(
            Status.err(SlaveOfflineError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_log_enable_get_not_exist_program(self):
        api_response = self.client.get(
            reverse('frontend:log_enable', args=[999999]))
        self.assertEqual(200, api_response.status_code)
        self.assertStatusRegex(
            Status.err(ProgramNotExistError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_log_enable_get_not_exist_log(self):
        slave = SlaveFactory(online=True)
        prog = ProgramFactory(slave=slave)

        api_response = self.client.get(
            reverse('frontend:log_enable', args=[prog.id]))
        self.assertEqual(200, api_response.status_code)

        self.assertStatusRegex(
            Status.err(LogNotExistError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_log_enable_post_forbidden(self):
        api_response = self.client.post(
            reverse('frontend:log_enable', args=[999999]))
        self.assertEqual(403, api_response.status_code)


class SlaveTests(StatusTestCase):
    def test_update_unknown_slave(self):
        res = self.client.put(reverse('frontend:slave_entry', args=['1234']))

        self.assertEqual(res.status_code, 200)

        self.assertStatusRegex(
            Status.err(SlaveNotExistError),
            Status.from_json(res.content.decode('utf-8')),
        )

    def test_wol_no_slave(self):
        #  non existent slave
        res = self.client.get(
            path=reverse(
                'frontend:slave_wol',
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
        res = self.client.post(
            path=reverse(
                'frontend:slave_wol',
                args=[slave.id],
            ))

        self.assertEqual(res.status_code, 403)

    def test_wol_success(self):
        slave = SlaveFactory()
        res = self.client.get(
            path=reverse(
                'frontend:slave_wol',
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
        response = self.client.get(
            "/api/slaves?q=" + str(slave.name[:name_half]))
        self.assertContains(response, slave.name)
        response = self.client.get("/api/slaves?q=" + str(slave.name))
        self.assertContains(response, slave.name)

    def test_add_slave_success(self):
        slave = SlaveFactory.build()

        api_response = self.client.post(
            reverse('frontend:slave_set'), {
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
            reverse('frontend:slave_set'), {
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
            reverse('frontend:slave_set'), {
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
        api_response = self.client.put(reverse('frontend:slave_set'))
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

    def test_slave_shutdown(self):
        slave = SlaveFactory(online=True)

        #  connect slave to websocket
        ws_client = WSClient()
        ws_client.join_group('client_' + str(slave.id))

        #  make request
        api_response = self.client.get(
            path=reverse(
                'frontend:slave_shutdown',
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

    def test_slave_shutdown_unknown_slave(self):
        #  make request
        api_response = self.client.get('/api/slave/111/shutdown')

        self.assertEqual(api_response.status_code, 200)
        self.assertStatusRegex(
            Status.err(SlaveNotExistError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_slave_shutdown_offline_slave(self):
        slave = SlaveFactory()

        #  make request
        api_response = self.client.get(
            reverse(
                'frontend:slave_shutdown',
                args=[slave.id],
            ))

        self.assertEqual(api_response.status_code, 200)
        self.assertStatusRegex(
            Status.err(SlaveOfflineError),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_slave_shutdown_forbidden_function(self):
        api_response = self.client.delete('/api/slave/1/shutdown')
        self.assertEqual(403, api_response.status_code)

    def test_query_get_all_files(self):
        resp = self.client.get("/api/slaves?filesystems=1")

        self.assertEqual(
            Status.ok([]),
            Status.from_json(resp.content.decode('utf-8')),
        )

        resp = self.client.get("/api/slaves?filesystems=1")

        self.assertEqual(
            Status.ok([]),
            Status.from_json(resp.content.decode('utf-8')),
        )

        filesystem = FileFactory()

        resp = self.client.get("/api/slaves?filesystems=1")

        self.assertEqual(
            Status.ok([filesystem.slave.name]),
            Status.from_json(resp.content.decode('utf-8')),
        )

    def test_query_get_all_same(self):
        resp = self.client.get("/api/slaves?programs=1&filesystems=1")

        self.assertStatusRegex(
            Status.err(SimultaneousQueryError),
            Status.from_json(resp.content.decode('utf-8')),
        )

    def test_query_get_all_slaves(self):
        resp = self.client.get("/api/slaves")
        self.assertEqual(
            Status.ok([]),
            Status.from_json(resp.content.decode('utf-8')),
        )

        slave = SlaveFactory()

        resp = self.client.get("/api/slaves")
        self.assertEqual(
            Status.ok([slave.name]),
            Status.from_json(resp.content.decode('utf-8')),
        )

    def test_query_get_all_programs(self):
        resp = self.client.get("/api/slaves?programs=1")

        self.assertEqual(
            Status.ok([]),
            Status.from_json(resp.content.decode('utf-8')),
        )

        resp = self.client.get("/api/slaves?programs=1")

        self.assertEqual(
            Status.ok([]),
            Status.from_json(resp.content.decode('utf-8')),
        )

        program = ProgramFactory()

        resp = self.client.get("/api/slaves?programs=1")

        self.assertEqual(
            Status.ok([program.slave.name]),
            Status.from_json(resp.content.decode('utf-8')),
        )
