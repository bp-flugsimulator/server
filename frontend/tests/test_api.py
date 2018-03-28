"""
TESTCASES NAMEING SCHEME

def test_<API>_<HTTP METHOD>_<LIST>:
  pass

<API>:
    the name of handler method without the type information (e.g.
    filesystem_set -> set)

<HTTP METHOD>:
    The used http method in the test function

 <LIST>:
    forbidden       -> method not allowed
    not_exist       -> the addressed object does not exist
    offline         -> the slave is offline
    success         -> example successfull request
    exist           -> the request is not successfull because something exists
                       or is running
    <ERROR>_error   -> any kind of error that is raised and catched in the API
"""
# pylint: disable=missing-docstring,too-many-public-methods

import json
import os

from urllib.parse import urlencode
from shlex import split

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
    ScriptRunningError,
    IdentifierError,
    PositiveNumberError,
    QueryParameterError,
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


class ScriptTest(StatusTestCase):
    def test_set_put_forbidden(self):
        response = self.client.put(reverse("frontend:script_set"))
        self.assertEqual(response.status_code, 403)

    def test_set_post_type_error(self):
        response = self.client.post(
            reverse("frontend:script_set"),
            '{"name": "test", "programs": [], "filesystems": [null]}',
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

    def test_set_post_negtaive_index_error(self):
        program = ProgramFactory()
        script = ScriptFactory.build()

        data = {
            "name":
            script.name,
            "programs": [{
                "slave": program.slave.id,
                "program": program.id,
                "index": -1,
            }],
            "filesystems": [],
        }

        response = self.client.post(
            reverse("frontend:script_set"),
            data=json.dumps(data),
            content_type="application/text",
        )
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(PositiveNumberError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_set_post_not_exist(self):
        program = ProgramFactory()
        script = ScriptFactory.build()

        data = {
            "name": script.name,
            "programs": [{
                "slave": -1,
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

        self.assertStatusRegex(
            Status.err(SlaveNotExistError),
            Status.from_json(response.content.decode('utf-8')),
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
        self.assertEqual(response.status_code, 200)

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

    def test_entry_post_forbidden(self):
        response = self.client.post(reverse("frontend:script_entry", args=[0]))
        self.assertEqual(response.status_code, 403)

    def test_entry_delete_not_exist(self):
        response = self.client.delete(
            reverse("frontend:script_entry", args=['0']))
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

        response = self.client.delete(
            reverse("frontend:script_entry", args=[db_script.id]), )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ScriptModel.objects.filter(name=script_name).exists())

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
            reverse("frontend:script_entry", args=[db_script.id]), )
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

    def test_entry_put_success(self):
        script = ScriptFactory()
        SGPFactory(script=script)
        SGFFactory(script=script)
        script_script = Script.from_model(script.id, "str", "str", "str")

        response = self.client.put(
            reverse("frontend:script_entry", args=[script.id]),
            data=json.dumps(dict(script_script)),
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(""),
            Status.from_json(response.content.decode('utf-8')),
        )

        slave2 = SlaveFactory()
        filesystem2 = FileFactory(slave=slave2)
        sgf2 = SGFFactory.build(script=script, filesystem=filesystem2)

        script_script.filesystems.append(
            ScriptEntryFilesystem(
                sgf2.index,
                sgf2.filesystem.name,
                sgf2.filesystem.slave.name,
            ), )

        response = self.client.put(
            reverse("frontend:script_entry", args=[script.id]),
            data=json.dumps(dict(script_script)),
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(""),
            Status.from_json(response.content.decode('utf-8')),
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
        response = self.client.put(
            reverse("frontend:script_entry", args=[script.id]),
            data=json.dumps(dict(script_script)),
        )
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "UNIQUE constraint failed")

    def test_entry_get_query_parameter_error(self):
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

        db_script = ScriptModel.objects.get(name=script_name)

        response = self.client.get(
            reverse(
                "frontend:script_entry",
                args=[db_script.id],
            ),
            {'slaves': 'no'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(QueryParameterError),
            Status.from_json(response.content.decode('utf-8')),
        )

        response = self.client.get(
            reverse(
                "frontend:script_entry",
                args=[db_script.id],
            ),
            {'programs': 'no'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(QueryParameterError),
            Status.from_json(response.content.decode('utf-8')),
        )

        response = self.client.get(
            reverse(
                "frontend:script_entry",
                args=[db_script.id],
            ),
            {'filesystems': 'no'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(QueryParameterError),
            Status.from_json(response.content.decode('utf-8')),
        )

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
            reverse(
                "frontend:script_entry",
                args=[db_script.id],
            ),
            {'slaves': 'int'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(dict(script_int)),
            Status.from_json(response.content.decode('utf-8')),
        )

        response = self.client.get(
            reverse(
                "frontend:script_entry",
                args=[db_script.id],
            ),
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
            reverse(
                "frontend:script_entry",
                args=[db_script.id],
            ),
            {'programs': 'int'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(dict(script_int)),
            Status.from_json(response.content.decode('utf-8')),
        )

        response = self.client.get(
            reverse(
                "frontend:script_entry",
                args=[db_script.id],
            ),
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
            reverse(
                "frontend:script_entry",
                args=[db_script.id],
            ),
            {'filesystems': 'int'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(dict(script_int)),
            Status.from_json(response.content.decode('utf-8')),
        )

        response = self.client.get(
            reverse(
                "frontend:script_entry",
                args=[db_script.id],
            ),
            {'filesystems': 'str'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(dict(script_str)),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_copy_post_success(self):
        script = ScriptFactory()
        sgp = SGPFactory(script=script)
        sgf = SGFFactory(script=script)

        response = self.client.post(
            reverse('frontend:script_copy', args=[str(script.id)]))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(''),
            Status.from_json(response.content.decode('utf-8')),
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
            response = self.client.post(
                reverse(
                    'frontend:script_copy',
                    args=[script.id],
                ))
            self.assertEqual(response.status_code, 200)

            self.assertEqual(
                Status.ok(''),
                Status.from_json(response.content.decode('utf-8')),
            )
            copy_name = "{}_copy_{}".format(script.name, i)
            self.assertTrue(
                ScriptModel.objects.filter(name=copy_name).exists())

    def test_copy_post_not_exist(self):
        response = self.client.post(
            reverse(
                'frontend:script_copy',
                args=[0],
            ))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(ScriptNotExistError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_copy_delete_forbidden(self):
        response = self.client.delete(
            reverse('frontend:script_copy', args=['0']))
        self.assertEqual(403, response.status_code)

    def test_run_put_forbidden(self):
        response = self.client.put(reverse("frontend:script_run", args=[0]))
        self.assertEqual(response.status_code, 403)

    def test_run_post_running_error(self):
        script = ScriptFactory(is_running=True, is_initialized=True)
        response = self.client.post(
            reverse("frontend:script_run", args=[script.id]))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(ScriptRunningError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_run_post_not_exist(self):
        response = self.client.post(reverse("frontend:script_run", args=[0]))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(ScriptNotExistError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_stop_put_forbidden(self):
        response = self.client.put(reverse('frontend:script_stop'))
        self.assertEqual(403, response.status_code)

    def test_stop_post_success(self):
        script = ScriptFactory(is_running=False, is_initialized=True)
        response = self.client.post(
            reverse("frontend:script_run", args=[script.id]))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse("frontend:script_stop"))
        self.assertEqual(response.status_code, 200)

    def test_set_default_forbidden(self):
        response = self.client.put(
            reverse('frontend:script_set_default', args=[0]))
        self.assertEqual(403, response.status_code)

    def test_set_default_success(self):
        script1 = ScriptFactory(last_ran=True)
        script2 = ScriptFactory()

        response = self.client.post(
            reverse("frontend:script_set_default", args=[script2.id]))
        self.assertEqual(response.status_code, 200)

        self.assertTrue(ScriptModel.objects.get(id=script2.id).last_ran)
        self.assertFalse(ScriptModel.objects.get(id=script1.id).last_ran)


class FilesystemTests(StatusTestCase):
    def test_set_delete_forbidden(self):
        response = self.client.delete(reverse("frontend:filesystem_set"))
        self.assertEqual(response.status_code, 403)

    def test_set_post_success(self):
        slave = SlaveFactory()
        filesystem = FileFactory.build()

        # add all programs
        response = self.client.post(
            reverse("frontend:filesystem_set"), {
                'name': filesystem.name,
                'source_path': filesystem.source_path,
                'source_type': filesystem.source_type,
                'destination_path': filesystem.destination_path,
                'destination_type': filesystem.destination_type,
                'slave': str(slave.id)
            })
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(''),
            Status.from_json(response.content.decode('utf-8')),
        )

        self.assertTrue(
            FilesystemModel.objects.filter(
                name=filesystem.name,
                source_path=filesystem.source_path,
                destination_path=filesystem.destination_path,
                slave=slave,
            ))

    def test_set_post_value_error(self):
        slave = SlaveFactory()
        filesystem = FileFactory.build()

        long_str = ''

        for _ in range(2000):
            long_str += 'a'

        response = self.client.post(
            reverse("frontend:filesystem_set"), {
                'name': long_str,
                'source_path': filesystem.source_path,
                'source_type': filesystem.source_type,
                'destination_path': filesystem.destination_path,
                'destination_type': filesystem.destination_type,
                'slave': str(slave.id)
            })
        self.assertEqual(200, response.status_code)

        self.assertEqual(
            Status.err({
                "name": [
                    "Ensure this value has at most 200 characters (it has 2000)."
                ],
            }),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_set_post_name_error(self):
        filesystem = FileFactory()

        # add all programs
        response = self.client.post(
            reverse("frontend:filesystem_set"), {
                'name': filesystem.name,
                'source_path': filesystem.source_path,
                'source_type': filesystem.source_type,
                'destination_path': filesystem.destination_path,
                'destination_type': filesystem.destination_type,
                'slave': str(filesystem.slave.id)
            })
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.err({
                'name':
                ['Filesystem with this Name already exists on this Client.']
            }),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_set_post_path_error(self):
        filesystem = FileFactory()

        response = self.client.post(
            reverse("frontend:filesystem_set"), {
                'name': filesystem.name + "new",
                'source_path': filesystem.source_path,
                'source_type': filesystem.source_type,
                'destination_path': filesystem.destination_path,
                'destination_type': filesystem.destination_type,
                'slave': str(filesystem.slave.id)
            })
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.err({
                'source_path': [
                    'Filesystem with this source path and destination path already exists on this Client.'
                ],
                'destination_path': [
                    'Filesystem with this source path and destination path already exists on this Client.'
                ],
            }),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_set_post_exist(self):
        slave = SlaveFactory()

        response = self.client.post(
            reverse('frontend:slave_set'),
            {
                'name': slave.name,
                'ip_address': slave.ip_address,
                'mac_address': slave.mac_address
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Status.err({
                "name": ["Slave with this Name already exists."],
                "ip_address": ["Slave with this Ip address already exists."],
                "mac_address": ["Slave with this Mac address already exists."]
            }),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_set_post_validation_error(self):
        slave = SlaveFactory.build(mac_address="0", ip_address="0")

        response = self.client.post(
            reverse('frontend:slave_set'),
            {
                'name': slave.name,
                'ip_address': slave.ip_address,
                'mac_address': slave.mac_address
            },
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.err({
                "ip_address": ["Enter a valid IPv4 or IPv6 address."],
                "mac_address": ["Enter a valid MAC Address."]
            }),
            Status.from_json(response.content.decode('utf-8')),
        )

        self.assertFalse(
            SlaveModel.objects.filter(
                name=slave.name,
                ip_address=slave.ip_address,
                mac_address=slave.mac_address,
            ).exists())

    def test_set_get_query_success(self):
        response = self.client.get(reverse("frontend:filesystem_set"))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok([]),
            Status.from_json(response.content.decode('utf-8')),
        )

        filesystem = FileFactory()

        # create more
        f1 = FileFactory()
        f2 = FileFactory()
        f3 = FileFactory()
        name_half = int(len(filesystem.name) / 2)

        response = self.client.get(
            reverse("frontend:filesystem_set"),
            {'q': filesystem.name[:name_half]})
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok([filesystem.name]),
            Status.from_json(response.content.decode('utf-8')),
        )

        response = self.client.get(
            reverse("frontend:filesystem_set"), {'q': filesystem.name})
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok([filesystem.name]),
            Status.from_json(response.content.decode('utf-8')),
        )

        response = self.client.get(reverse("frontend:filesystem_set"))
        self.assertEqual(response.status_code, 200)

        status = Status.from_json(response.content.decode('utf-8'))
        self.assertTrue(status.is_ok())
        self.assertEqual(
            set(map(str, [filesystem, f1, f2, f3])),
            set(status.payload),
        )

    def test_set_get_query_slaves_success(self):
        filesystem = FileFactory()

        with_str = self.client.get(
            reverse('frontend:filesystem_set'),
            {
                'slave': filesystem.slave.name,
                'is_string': 'True'
            },
        )
        self.assertEqual(with_str.status_code, 200)

        without_str = self.client.get(
            reverse('frontend:filesystem_set'),
            {
                'slave': filesystem.slave.id,
                'is_string': 'False'
            },
        )
        self.assertEqual(without_str.status_code, 200)

        ints = self.client.get(
            reverse('frontend:filesystem_set'),
            {'slave': filesystem.slave.id},
        )
        self.assertEqual(ints.status_code, 200)

        with_str = Status.from_json(with_str.content.decode('utf-8'))
        ints = Status.from_json(ints.content.decode('utf-8'))
        without_str = Status.from_json(without_str.content.decode('utf-8'))

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

    def test_set_get_query_identifier_error(self):
        response = self.client.get(
            reverse("frontend:filesystem_set"),
            {'slave': 'not_an_int'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(IdentifierError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_set_get_query_not_exist_error(self):
        response_int = self.client.get(
            reverse("frontend:filesystem_set"),
            {'slave': 0},
        )
        self.assertEqual(response_int.status_code, 200)

        self.assertStatusRegex(
            Status.err(SlaveNotExistError),
            Status.from_json(response_int.content.decode('utf-8')),
        )

        response_str = self.client.get(
            reverse("frontend:filesystem_set"),
            {
                'slave': "none",
                'is_string': 'True'
            },
        )
        self.assertEqual(response_str.status_code, 200)

        self.assertStatusRegex(
            Status.err(SlaveNotExistError),
            Status.from_json(response_str.content.decode('utf-8')),
        )

    def test_entry_post_forbidden(self):
        response = self.client.post(
            reverse("frontend:filesystem_entry", args=['0']))
        self.assertEqual(response.status_code, 403)

    def test_entry_delete_not_exist(self):
        response = self.client.delete(
            reverse("frontend:filesystem_entry", args=['0']))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(FilesystemNotExistError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_delete_success(self):
        filesystem = FileFactory()
        response = self.client.delete(
            reverse("frontend:filesystem_entry", args=[filesystem.id]))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(''),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_delete_deleted_error(self):
        filesystem = FileFactory(hash_value="Some")
        response = self.client.delete(
            reverse("frontend:filesystem_entry", args=[filesystem.id]))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(FilesystemDeleteError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_put_success(self):
        filesystem = FileFactory()
        slave = filesystem.slave

        response = self.client.put(
            reverse("frontend:filesystem_entry", args=[filesystem.id]),
            data=urlencode({
                'name': "edit_filesystem_" + str(slave.id),
                'source_path': str(slave.id),
                'destination_path': str(slave.id),
                'slave': str(slave.id),
                'source_type': filesystem.source_type,
                'destination_type': filesystem.destination_type,
            }))
        self.assertEqual(200, response.status_code)

        self.assertEqual(
            Status.ok(''),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_put_validation_error(self):
        filesystem = FileFactory(name="", source_path="", destination_path="")
        slave = filesystem.slave

        long_str = ''
        for _ in range(2000):
            long_str += 'a'

        response = self.client.put(
            reverse("frontend:filesystem_entry", args=[filesystem.id]),
            data=urlencode({
                'name': long_str,
                'source_path': long_str,
                'destination_path': long_str,
                'slave': str(slave.id),
                'source_type': filesystem.source_type,
                'destination_type': filesystem.destination_type,
            }))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.err({
                "name": [
                    "Ensure this value has at most 200 characters (it has 2000)."
                ],
            }),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_put_not_exist(self):
        response = self.client.put(
            reverse("frontend:filesystem_entry", args=[0]))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(FilesystemNotExistError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_put_exists(self):
        filesystem_exists = FileFactory()
        filesystem_edit = FileFactory(slave=filesystem_exists.slave)

        response = self.client.put(
            reverse("frontend:filesystem_entry", args=[filesystem_edit.id]),
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

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.err({
                "name":
                ["Filesystem with this Name already exists on this Client."]
            }),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_restore_post_not_exist(self):
        response = self.client.post(
            reverse("frontend:filesystem_restore", args=['0']))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(FilesystemNotExistError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_restore_post_offline(self):
        slave = SlaveFactory(online=False)
        filesystem = FileFactory(slave=slave)

        ws_client = WSClient()
        ws_client.join_group('client_' + str(slave.id))

        restore_response = self.client.post(
            reverse("frontend:filesystem_restore", args=[filesystem.id]))
        self.assertEqual(restore_response.status_code, 200)

        self.assertIsNone(ws_client.receive())

        self.assertStatusRegex(
            Status.err(SlaveOfflineError),
            Status.from_json(restore_response.content.decode('utf-8')),
        )

    def test_restore_post_exists(self):
        slave = SlaveFactory(online=True)
        filesystem = FileFactory(slave=slave)

        # connect slave to websocket
        ws_client = WSClient()
        ws_client.join_group('client_' + str(slave.id))

        response = self.client.post(
            reverse("frontend:filesystem_restore", args=[filesystem.id]))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(FilesystemNotMovedError),
            Status.from_json(response.content.decode('utf-8')),
        )

        self.assertIsNone(ws_client.receive())

    def test_restore_post_success(self):
        slave = SlaveFactory(online=True)
        filesystem = MovedFileFactory(slave=slave)

        # connect slave to websocket
        ws_client = WSClient()
        ws_client.join_group('client_' + str(slave.id))

        response = self.client.post(
            reverse("frontend:filesystem_restore", args=[filesystem.id]))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.from_json(response.content.decode('utf-8')),
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

    def test_restore_put_forbidden(self):
        response = self.client.put(
            reverse("frontend:filesystem_restore", args=['0']))
        self.assertEqual(response.status_code, 403)

    def test_move_put_forbidden(self):
        response = self.client.put(
            reverse("frontend:filesystem_move", args=['0']))
        self.assertEqual(response.status_code, 403)

    def test_move_post_offline_error(self):
        filesystem = FileFactory()

        response = self.client.post(
            reverse("frontend:filesystem_move", args=[filesystem.id]))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(SlaveOfflineError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_move_post_not_exist(self):
        response = self.client.post(
            reverse("frontend:filesystem_move", args=['0']))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(FilesystemNotExistError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_move_post_success(self):
        slave = SlaveFactory(online=True)
        filesystem = FileFactory(slave=slave)

        # connect slave to websocket
        ws_client = WSClient()
        ws_client.join_group('client_' + str(slave.id))

        response = self.client.post(
            reverse("frontend:filesystem_move", args=[filesystem.id]))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.from_json(response.content.decode('utf-8')),
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

        # case directory
        filesystem = FileFactory(
            slave=slave, source_type="dir", destination_type="dir")

        # connect slave to websocket
        ws_client = WSClient()
        ws_client.join_group('client_' + str(slave.id))

        response = self.client.post(
            reverse("frontend:filesystem_move", args=[filesystem.id]))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.from_json(response.content.decode('utf-8')),
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

    def test_move_post_conflict_success(self):
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

        response = self.client.post(
            reverse("frontend:filesystem_move", args=[filesystem.id]))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.from_json(response.content.decode('utf-8')),
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

    def test_move_post_exists_error(self):
        slave = SlaveFactory(online=True)
        filesystem = MovedFileFactory(slave=slave)

        # connect slave to websocket
        ws_client = WSClient()
        ws_client.join_group('client_' + str(slave.id))

        response = self.client.post(
            reverse("frontend:filesystem_move", args=[filesystem.id]))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(FilesystemMovedError.regex_string()),
            Status.from_json(response.content.decode('utf-8')),
        )

        self.assertIsNone(ws_client.receive())

    def test_move_post_offline(self):
        slave = SlaveFactory(online=False)
        filesystem = FileFactory(slave=slave)

        ws_client = WSClient()
        ws_client.join_group('client_' + str(slave.id))

        move_response = self.client.post(
            reverse("frontend:filesystem_move", args=[filesystem.id]))
        self.assertEqual(move_response.status_code, 200)

        self.assertIsNone(ws_client.receive())

        self.assertStatusRegex(
            Status.err(SlaveOfflineError),
            Status.from_json(move_response.content.decode('utf-8')),
        )

class ProgramTests(StatusTestCase):
    def test_set_delete_query_forbidden(self):
        response = self.client.delete(reverse("frontend:program_set"))
        self.assertEqual(response.status_code, 403)

    def test_set_get_query_success(self):
        response = self.client.get(reverse("frontend:program_set"))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok([]),
            Status.from_json(response.content.decode('utf-8')),
        )

        program = ProgramFactory()

        # create more
        f1 = ProgramFactory()
        f2 = ProgramFactory()
        f3 = ProgramFactory()
        name_half = int(len(program.name) / 2)

        response = self.client.get(
            reverse("frontend:program_set"), {'q': program.name[:name_half]})

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok([program.name]),
            Status.from_json(response.content.decode('utf-8')),
        )

        response = self.client.get(
            reverse("frontend:program_set"), {'q': program.name})
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok([program.name]),
            Status.from_json(response.content.decode('utf-8')),
        )

        response = self.client.get(reverse("frontend:program_set"))
        self.assertEqual(response.status_code, 200)

        status = Status.from_json(response.content.decode('utf-8'))
        self.assertTrue(status.is_ok())

        self.assertEqual(
            set(map(str, [program, f1, f2, f3])),
            set(status.payload),
        )

    def test_set_get_query_slaves_success(self):
        program = FileFactory()

        with_str = self.client.get(
            reverse('frontend:program_set'),
            {
                'slave': program.slave.name,
                'is_string': 'True'
            },
        )
        self.assertEqual(with_str.status_code, 200)

        without_str = self.client.get(
            reverse('frontend:program_set'),
            {
                'slave': program.slave.id,
                'is_string': 'False'
            },
        )
        self.assertEqual(without_str.status_code, 200)

        ints = self.client.get(
            reverse('frontend:program_set'),
            {'slave': program.slave.id},
        )
        self.assertEqual(ints.status_code, 200)

        with_str = Status.from_json(with_str.content.decode('utf-8'))
        ints = Status.from_json(ints.content.decode('utf-8'))
        without_str = Status.from_json(without_str.content.decode('utf-8'))

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

    def test_set_get_query_identifier_error(self):
        response = self.client.get(
            reverse("frontend:program_set"),
            {'slave': 'not_an_int'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(IdentifierError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_set_get_query_not_exist_error(self):
        response_int = self.client.get(
            reverse("frontend:program_set"),
            {'slave': 0},
        )
        self.assertEqual(response_int.status_code, 200)

        self.assertStatusRegex(
            Status.err(SlaveNotExistError),
            Status.from_json(response_int.content.decode('utf-8')),
        )

        response_str = self.client.get(
            reverse("frontend:program_set"),
            {
                'slave': "none",
                'is_string': 'True'
            },
        )
        self.assertEqual(response_str.status_code, 200)

        self.assertStatusRegex(
            Status.err(SlaveNotExistError),
            Status.from_json(response_str.content.decode('utf-8')),
        )

    def test_set_post_success(self):
        slave = SlaveFactory()

        response = self.client.post(
            reverse('frontend:program_set'), {
                'name': 'name' + str(slave.id),
                'path': 'path' + str(slave.id),
                'arguments': 'arguments' + str(slave.id),
                'slave': str(slave.id),
                'start_time': -1,
            })
        self.assertEqual(200, response.status_code)

        self.assertEqual(
            Status.ok(''),
            Status.from_json(response.content.decode('utf-8')),
        )

        # test if all programs are in the database
        self.assertTrue(
            ProgramModel.objects.filter(
                name='name' + str(slave.id),
                path='path' + str(slave.id),
                arguments='arguments' + str(slave.id),
                slave=slave,
            ))

    def test_set_post_too_long_error(self):
        slave = SlaveFactory()

        long_str = ''

        for _ in range(2000):
            long_str += 'a'

        response = self.client.post(
            reverse('frontend:program_set'), {
                'name': long_str,
                'path': long_str,
                'arguments': long_str,
                'slave': str(slave.id),
                'start_time': -1,
            })
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.err({
                "name": [
                    "Ensure this value has at most 1000 characters (it has 2000)."
                ],
            }),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_set_post_value_error(self):
        program = ProgramFactory()

        # try to add program with the same name
        response = self.client.post(
            reverse('frontend:program_set'), {
                'name': program.name,
                'path': program.path,
                'arguments': program.arguments,
                'slave': str(program.slave.id),
                'start_time': program.start_time,
            })
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.err({
                'name':
                ['Program with this Name already exists on this Client.']
            }),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_post_forbidden(self):
        response = self.client.post(
            reverse("frontend:program_entry", args=[0]))
        self.assertEqual(response.status_code, 403)

    def test_entry_delete_not_exist(self):
        response = self.client.delete(
            reverse("frontend:program_entry", args=['0']))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(ProgramNotExistError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_delete_success(self):
        program = ProgramFactory()

        response = self.client.delete(
            reverse("frontend:program_entry", args=[program.id]))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(''),
            Status.from_json(response.content.decode('utf-8')),
        )

        self.assertFalse(
            ProgramModel.objects.filter(name=program.name).exists())

    def test_entry_put_success(self):
        program = ProgramFactory()
        slave = program.slave

        response = self.client.put(
            reverse("frontend:program_entry", args=[program.id]),
            data=urlencode({
                'name': "edit_program_" + str(slave.id),
                'path': str(slave.id),
                'arguments': str(slave.id),
                'start_time': slave.id,
                'slave': str(slave.id),
            }))
        self.assertEqual(200, response.status_code)

        self.assertEqual(
            Status.ok(''),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_put_validation_error(self):
        program = ProgramFactory()

        long_str = ''
        for _ in range(2000):
            long_str += 'a'

        response = self.client.put(
            reverse("frontend:program_entry", args=[program.id]),
            data=urlencode({
                'name': long_str,
                'path': program.path,
                'arguments': program.arguments,
                'start_time': program.start_time,
                'slave': str(program.slave.id),
            }))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.err({
                "name": [
                    "Ensure this value has at most 1000 characters (it has 2000)."
                ],
            }),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_put_not_exist(self):
        response = self.client.put(reverse("frontend:program_entry", args=[0]))

        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(ProgramNotExistError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_put_exists(self):
        program_exist = ProgramFactory()
        program_edit = ProgramFactory(slave=program_exist.slave)

        response = self.client.put(
            reverse("frontend:program_entry", args=[program_edit.id]),
            data=urlencode({
                'name': program_exist.name,
                'path': program_exist.path,
                'arguments': program_exist.arguments,
                'start_time': program_exist.start_time,
                'slave': str(program_exist.slave.id),
            }))

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.err({
                "name":
                ["Program with this Name already exists on this Client."]
            }),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_start_post_success(self):
        slave = SlaveOnlineFactory()
        program = ProgramFactory(slave=slave)

        #  connect client
        client = WSClient()
        client.join_group("client_" + str(slave.id))

        #  connect webinterface to /notifications
        webinterface = WSClient()
        webinterface.join_group('notifications')

        response = self.client.post(
            reverse('frontend:program_start', args=[program.id]))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(''),
            Status.from_json(response.content.decode('utf-8')),
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

    def test_start_post_not_exist(self):
        response = self.client.post(
            reverse('frontend:program_start', args=[0]))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(ProgramNotExistError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_start_post_offline(self):
        program = ProgramFactory()
        slave = program.slave

        client = WSClient()
        client.join_group("commands_" + str(slave.id))

        response = self.client.post(
            reverse('frontend:program_start', args=[program.id]))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(SlaveOfflineError),
            Status.from_json(response.content.decode('utf-8')),
        )

        self.assertIsNone(client.receive())

    def test_start_post_exist(self):
        slave = SlaveFactory(online=True)
        program = ProgramFactory(slave=slave)
        ProgramStatusFactory(program=program, running=True)

        response = self.client.post(
            reverse('frontend:program_start', args=[program.id]))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(ProgramRunningError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_start_delete_forbidden(self):
        response = self.client.delete(
            reverse('frontend:program_start', args=['0']))
        self.assertEqual(403, response.status_code)

    def test_stop_post_success(self):
        slave = SlaveFactory(online=True)
        program = ProgramFactory(slave=slave)
        status = ProgramStatusFactory(program=program, running=True)

        slave_ws = WSClient()
        slave_ws.join_group('client_' + str(slave.id))

        response = self.client.post(
            reverse(
                'frontend:program_stop',
                args=[program.id],
            ))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(''),
            Status.from_json(response.content.decode('utf-8')),
        )

        self.assertEqual(
            Command(method='execute', uuid=status.command_uuid),
            Command.from_json(json.dumps(slave_ws.receive())),
        )

    def test_stop_post_offline(self):
        program = ProgramFactory()

        response = self.client.post(
            reverse('frontend:program_stop', args=[program.id]))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(SlaveOfflineError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_stop_post_not_exist(self):
        response = self.client.post(
            reverse(
                'frontend:program_stop',
                args=[9999],
            ))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(ProgramNotExistError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_stop_post_not_running_error(self):
        slave = SlaveFactory(online=True)
        program = ProgramFactory(slave=slave)
        ProgramStatusFactory(program=program, running=False)

        response = self.client.post(
            reverse(
                'frontend:program_stop',
                args=[program.id],
            ))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(ProgramNotRunningError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_stop_delete_forbidden(self):
        response = self.client.delete(
            reverse(
                'frontend:program_stop',
                args=[0],
            ))
        self.assertEqual(response.status_code, 403)

    def test_log_entry_get_success(self):
        slave = SlaveFactory(online=True)
        program = ProgramFactory(slave=slave)
        status = ProgramStatusFactory(running=True, program=program)

        ws_slave = WSClient()
        ws_slave.join_group('client_' + str(slave.id))

        response = self.client.get(
            reverse('frontend:program_log_entry', args=[program.id]))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(''),
            Status.from_json(response.content.decode('utf-8')),
        )

        self.assertEqual(
            Command(
                method='get_log',
                target_uuid=status.command_uuid,
            ),
            Command.from_json(json.dumps(ws_slave.receive())),
        )

    def test_log_entry_get_not_exist(self):
        response = self.client.get(
            reverse('frontend:program_log_entry', args=[0]))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(ProgramNotExistError),
            Status.from_json(response.content.decode('utf-8')),
        )

        slave = SlaveFactory(online=True)
        program = ProgramFactory(slave=slave)

        response = self.client.get(
            reverse('frontend:program_log_entry', args=[program.id]))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(LogNotExistError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_log_entry_delete_forbidden(self):
        response = self.client.delete(
            reverse('frontend:program_log_entry', args=[0]))
        self.assertEqual(response.status_code, 403)

    def test_log_disable_post_success(self):
        slave = SlaveFactory(online=True)
        program = ProgramFactory(slave=slave)
        status = ProgramStatusFactory(running=True, program=program)

        ws_slave = WSClient()
        ws_slave.join_group('client_' + str(slave.id))

        response = self.client.post(
            reverse('frontend:program_log_disable', args=[program.id]))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(''),
            Status.from_json(response.content.decode('utf-8')),
        )

        self.assertEqual(
            Command(
                method='disable_logging',
                target_uuid=status.command_uuid,
            ),
            Command.from_json(json.dumps(ws_slave.receive())),
        )

    def test_log_disable_post_offline(self):
        program = ProgramFactory()

        response = self.client.post(
            reverse('frontend:program_log_disable', args=[program.id]))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(SlaveOfflineError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_log_disable_post_not_exist(self):
        response = self.client.post(
            reverse('frontend:program_log_disable', args=[0]))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(ProgramNotExistError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_log_disable_delete_forbidden(self):
        response = self.client.delete(
            reverse('frontend:program_log_disable', args=[0]))
        self.assertEqual(response.status_code, 403)

    def test_log_enable_post_success(self):
        slave = SlaveFactory(online=True)
        program = ProgramFactory(slave=slave)
        status = ProgramStatusFactory(running=True, program=program)

        ws_slave = WSClient()
        ws_slave.join_group('client_' + str(slave.id))

        response = self.client.post(
            reverse('frontend:program_log_enable', args=[program.id]))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(''),
            Status.from_json(response.content.decode('utf-8')),
        )

        self.assertEqual(
            Command(
                method='enable_logging',
                target_uuid=status.command_uuid,
            ),
            Command.from_json(json.dumps(ws_slave.receive())),
        )

    def test_log_enable_post_offline_error(self):
        program = ProgramFactory()

        response = self.client.post(
            reverse('frontend:program_log_enable', args=[program.id]))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(SlaveOfflineError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_log_enable_post_not_exist(self):
        response = self.client.post(
            reverse('frontend:program_log_enable', args=[0]))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(ProgramNotExistError),
            Status.from_json(response.content.decode('utf-8')),
        )

        slave = SlaveFactory(online=True)
        prog = ProgramFactory(slave=slave)

        response = self.client.post(
            reverse('frontend:program_log_enable', args=[prog.id]))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(LogNotExistError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_log_enable_delete_forbidden(self):
        response = self.client.delete(
            reverse('frontend:program_log_enable', args=[0]))
        self.assertEqual(response.status_code, 403)


class SlaveTests(StatusTestCase):
    def test_set_post_success(self):
        slave = SlaveFactory.build()

        response = self.client.post(
            reverse('frontend:slave_set'), {
                'name': slave.name,
                'ip_address': slave.ip_address,
                'mac_address': slave.mac_address
            })
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(''),
            Status.from_json(response.content.decode('utf-8')),
        )

        self.assertTrue(SlaveModel.objects.filter(name=slave.name).exists())

    def test_set_delete_forbidden(self):
        response = self.client.delete(reverse("frontend:slave_set"))
        self.assertEqual(response.status_code, 403)

    def test_set_get_query_filesystem_success(self):
        response = self.client.get(
            reverse("frontend:slave_set"),
            {'filesystems': '1'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok([]),
            Status.from_json(response.content.decode('utf-8')),
        )

        response = self.client.get(
            reverse("frontend:slave_set"),
            {'filesystems': '1'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok([]),
            Status.from_json(response.content.decode('utf-8')),
        )

        filesystem = FileFactory()

        response = self.client.get(
            reverse("frontend:slave_set"),
            {'filesystems': '1'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok([filesystem.slave.name]),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_set_get_query_success(self):
        response = self.client.get(reverse("frontend:slave_set"))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok([]),
            Status.from_json(response.content.decode('utf-8')),
        )

        response = self.client.get(
            reverse("frontend:slave_set"),
            {'q': 'any'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok([]),
            Status.from_json(response.content.decode('utf-8')),
        )

        slave = SlaveFactory()

        response = self.client.get(reverse("frontend:slave_set"))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok([slave.name]),
            Status.from_json(response.content.decode('utf-8')),
        )

        response = self.client.get(
            reverse("frontend:slave_set"),
            {'q': slave.name[:int(len(slave.name) / 2)]},
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok([slave.name]),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_set_get_query_programs_success(self):
        response = self.client.get(
            reverse("frontend:slave_set"),
            {'programs': '1'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok([]),
            Status.from_json(response.content.decode('utf-8')),
        )

        response = self.client.get(
            reverse("frontend:slave_set"),
            {'programs': '1'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok([]),
            Status.from_json(response.content.decode('utf-8')),
        )

        program = ProgramFactory()

        response = self.client.get(
            reverse("frontend:slave_set"),
            {'programs': '1'},
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok([program.slave.name]),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_set_get_query_simultaneous_error(self):
        response = self.client.get(
            reverse("frontend:slave_set"),
            {
                'filesystems': 1,
                'programs': 1,
            },
        )
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(SimultaneousQueryError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_get_forbidden(self):
        response = self.client.get(reverse("frontend:slave_entry", args=[0]))
        self.assertEqual(response.status_code, 403)

    def test_entry_get_offline_slave(self):
        program = ProgramFactory()

        response = self.client.get(
            reverse('frontend:program_log_entry', args=[program.id]))
        self.assertEqual(200, response.status_code)

        self.assertStatusRegex(
            Status.err(SlaveOfflineError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_delete_not_exist(self):
        response = self.client.delete(
            reverse("frontend:slave_entry", args=['0']))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(SlaveNotExistError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_delete_success(self):
        slave = SlaveFactory()

        response = self.client.delete(
            reverse(
                "frontend:slave_entry",
                args=[slave.id],
            ), )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(''),
            Status.from_json(response.content.decode('utf-8')),
        )
        self.assertFalse(SlaveModel.objects.filter(id=slave.id).exists())

    def test_entry_put_success(self):
        slave = SlaveFactory()
        slave_new = SlaveFactory.build()

        response = self.client.put(
            reverse("frontend:slave_entry", args=[slave.id]),
            urlencode({
                'name': slave_new.name,
                'mac_address': slave_new.mac_address,
                'ip_address': slave_new.ip_address,
            }),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Status.ok(''),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_put_not_exist(self):
        res = self.client.put(reverse('frontend:slave_entry', args=[0]))
        self.assertEqual(res.status_code, 200)

        self.assertStatusRegex(
            Status.err(SlaveNotExistError),
            Status.from_json(res.content.decode('utf-8')),
        )

    def test_entry_put_value_error(self):
        program = ProgramFactory(name="", path="", arguments="")
        slave = program.slave

        long_str = ''
        for _ in range(2000):
            long_str += 'a'

        response = self.client.put(
            reverse('frontend:program_entry', args=[program.id]),
            data=urlencode({
                'name': long_str,
                'path': long_str,
                'arguments': long_str,
                'slave': str(slave.id),
                'start_time': -1,
            }))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.err({
                "name": [
                    "Ensure this value has at most 1000 characters (it has 2000)."
                ],
            }),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_put_unique_error(self):
        program_exists = ProgramFactory()
        program_edit = ProgramFactory(slave=program_exists.slave)

        response = self.client.put(
            reverse('frontend:program_entry', args=[program_edit.id]),
            data=urlencode({
                'name': program_exists.name,
                'path': program_exists.path,
                'arguments': program_exists.arguments,
                'slave': str(program_exists.slave.id),
                'start_time': -1,
            }))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.err({
                "name":
                ["Program with this Name already exists on this Client."]
            }),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_entry_put_exist(self):
        slave_exists = SlaveFactory()
        slave_edit = SlaveFactory()

        response = self.client.put(
            reverse("frontend:slave_entry", args=[slave_edit.id]),
            urlencode({
                'name': slave_exists.name,
                'ip_address': slave_exists.ip_address,
                'mac_address': slave_exists.mac_address,
            }),
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.err({
                "name": ["Slave with this Name already exists."],
                "ip_address": ["Slave with this Ip address already exists."],
                "mac_address": ["Slave with this Mac address already exists."],
            }),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_wol_post_success(self):
        slave = SlaveFactory()
        res = self.client.post(
            reverse(
                'frontend:slave_wol',
                args=[slave.id],
            ))
        self.assertEqual(res.status_code, 200)

        self.assertEqual(
            Status.ok(''),
            Status.from_json(res.content.decode('utf-8')),
        )

    def test_wol_post_not_exist(self):
        res = self.client.post(reverse(
            'frontend:slave_wol',
            args=[0],
        ))
        self.assertEqual(res.status_code, 200)

        self.assertStatusRegex(
            Status.err(SlaveNotExistError),
            Status.from_json(res.content.decode('utf-8')),
        )

    def test_wol_delete_forbidden(self):
        slave = SlaveFactory()

        res = self.client.delete(
            reverse(
                'frontend:slave_wol',
                args=[slave.id],
            ))

        self.assertEqual(res.status_code, 403)

    def test_shutdown_post_success(self):
        slave = SlaveFactory(online=True)

        ws_client = WSClient()
        ws_client.join_group('client_' + str(slave.id))

        response = self.client.post(
            reverse(
                'frontend:slave_shutdown',
                args=[slave.id],
            ))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Status.ok(''),
            Status.from_json(response.content.decode('utf-8')),
        )

        self.assertEqual(
            Command(method='shutdown'),
            Command.from_json(json.dumps(ws_client.receive())),
        )

    def test_shutdown_post_not_exist(self):
        response = self.client.post(
            reverse(
                "frontend:slave_shutdown",
                args=[111],
            ))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(SlaveNotExistError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_shutdown_post_offline(self):
        slave = SlaveFactory()

        response = self.client.post(
            reverse(
                'frontend:slave_shutdown',
                args=[slave.id],
            ))
        self.assertEqual(response.status_code, 200)

        self.assertStatusRegex(
            Status.err(SlaveOfflineError),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_shutdown_delete_forbidden(self):
        response = self.client.delete(
            reverse(
                "frontend:slave_shutdown",
                args=[0],
            ))
        self.assertEqual(response.status_code, 403)

    def test_stop_all_post_success(self):
        online_slaves = list()
        online_slave_websockets = list()

        for _ in range(1):
            slave = SlaveFactory(online=True)
            ws = WSClient()
            ws.join_group('client_' + str(slave.id))
            online_slave_websockets.append(ws)
            online_slaves.append(slave)

        offline_slave = SlaveFactory()
        offline_slave_websocket = WSClient()
        offline_slave_websocket.join_group('client_' + str(offline_slave.id))

        response = self.client.post(
            reverse("frontend:scope_operation"),
            {'scope': 'clients'
                })
        self.assertEqual(response.status_code, 200)

        self.assertIsNone(offline_slave_websocket.receive())

        self.assertEqual(
            Status.from_json(response.content.decode('utf-8')),
            Status.ok(''),
        )


    def test_stop_all_put_forbidden(self):
        response = self.client.put(
            reverse("frontend:scope_operation"))
        self.assertEqual(response.status_code, 403)
