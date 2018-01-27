#  pylint: disable=C0111,C0103

import json
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
    File as FileModel,
    Program as ProgramModel,
    ProgramStatus as ProgramStatusModel,
)

from .factory import (
    SlaveFactory,
    ProgramFactory,
    ScriptFactory,
    FileFactory,
    ProgramStatusFactory,
    SlaveStatusFactory,
)


class ScriptTest(TestCase):

    def test_script_delete(self):
        slave = SlaveFactory()
        program = ProgramFactory(slave=slave)
        file = FileFactory(slave=slave)
        script_name = ScriptFactory.build().name

        script = Script(
            script_name,
            [ScriptEntryProgram(0, program.name, slave.name)],
            [ScriptEntryFile(0, file.name, slave.name)],
        )
        script.save()

        db_script = ScriptModel.objects.get(name=script_name)

        response = self.client.delete("/api/script/" + str(db_script.id))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            ScriptModel.objects.filter(name=script_name).exists())

    def test_add_script_forbidden(self):
        response = self.client.put("/api/scripts")
        self.assertEqual(response.status_code, 403)

    def test_add_script_type_error(self):
        response = self.client.post(
            "/api/scripts",
            data='{"name": "test", "programs": [], "files": [null]}',
            content_type="application/json",
        )

        self.assertContains(
            response,
            "Wrong array items.",
        )

    def test_add_script_json_error(self):
        response = self.client.post(
            "/api/scripts", data={
                "name": "test",
                "programs": {},
                "files": {}
            })
        self.assertContains(
            response,
            "One or more values does contain not valid types.",
        )

    def test_add_script_value_error(self):
        response = self.client.post(
            "/api/scripts",
            data='{"name": "test", "programs": {}, "files": {}}',
            content_type="application/json",
        )
        self.assertContains(
            response,
            "One or more values does contain not valid types.",
        )

    def test_add_script_unique_error(self):
        response = self.client.post(
            "/api/scripts",
            data='{"name": "test", "programs":  [], "files": []}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '"status": "ok"')
        response = self.client.post(
            "/api/scripts",
            data='{"name": "test", "programs":  [], "files": []}',
            content_type="application/json",
        )
        self.assertContains(
            response,
            "Script with that name already exists.",
        )

    def test_add_script_key_error(self):
        response = self.client.post(
            "/api/scripts",
            data='{"name": "test", "program":  [], "files": []}',
            content_type="application/json",
        )
        self.assertContains(
            response,
            "Could not find required key {}".format("program"),
        )

    def test_add_script(self):
        response = self.client.post(
            "/api/scripts",
            data='{"name": "test", "programs":  [], "files": []}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '"status": "ok"')

    def test_get_script(self):
        slave = SlaveFactory()
        program = ProgramFactory(slave=slave)
        file = FileFactory(slave=slave)
        script_name = ScriptFactory.build().name

        script = Script(
            script_name,
            [ScriptEntryProgram(0, program.id, slave.id)],
            [ScriptEntryFile(0, file.id, slave.id)],
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
        response = self.client.get("/api/script/0?files=float")
        self.assertContains(response, "err")
        self.assertContains(
            response,
            "files only allow str or int. (given float)",
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
        file = FileFactory(slave=slave)
        script_name = ScriptFactory.build().name

        script = Script(
            script_name,
            [ScriptEntryProgram(0, program.id, slave.id)],
            [ScriptEntryFile(0, file.id, slave.id)],
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
        file = FileFactory(slave=slave)
        script_name = ScriptFactory.build().name

        script = Script(
            script_name,
            [ScriptEntryProgram(0, program.id, slave.id)],
            [ScriptEntryFile(0, file.id, slave.id)],
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
        file = FileFactory(slave=slave)
        script_name = ScriptFactory.build().name

        script = Script(
            script_name,
            [ScriptEntryProgram(0, program.id, slave.id)],
            [ScriptEntryFile(0, file.id, slave.id)],
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
        file = FileFactory(slave=slave)
        script_name = ScriptFactory.build().name

        script = Script(
            script_name,
            [ScriptEntryProgram(0, program.id, slave.id)],
            [ScriptEntryFile(0, file.id, slave.id)],
        )
        script.save()

        db_script = ScriptModel.objects.get(name=script_name)

        response = self.client.get(
            "/api/script/{}?programs=str&slaves=str&files=str".format(
                db_script.id))

        expected_json = dict(script)
        expected_json['programs'][0]['slave'] = slave.name
        expected_json['programs'][0]['program'] = program.name
        expected_json['files'][0]['file'] = file.name
        expected_json['files'][0]['slave'] = slave.name

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


class FileTests(TestCase):
    def test_file_autocomplete(self):
        file = FileFactory()
        name_half = int(len(file.name) / 2)

        response = self.client.get("/api/files?q=")
        self.assertContains(response, file.name)
        response = self.client.get("/api/files?q=" + str(
            file.name[:name_half]))
        self.assertContains(response, file.name)
        response = self.client.get("/api/files?q=" + str(file.name))
        self.assertContains(response, file.name)

    def test_add_file(self):
        slave = SlaveFactory()
        file = FileFactory.build()

        # add all programs
        api_response = self.client.post(
            '/api/files', {
                'name': file.name,
                'sourcePath': file.sourcePath,
                'destinationPath': file.destinationPath,
                'slave': str(slave.id)
            })

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.ok(''),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        self.assertTrue(
            FileModel.objects.filter(
                name=file.name,
                sourcePath=file.sourcePath,
                destinationPath=file.destinationPath,
                slave=slave,
            ))

    def test_add_file_fail_length(self):
        slave = SlaveFactory()

        long_str = ''

        for _ in range(2000):
            long_str += 'a'

        api_response = self.client.post('/api/files', {
            'name': long_str,
            'sourcePath': long_str,
            'destinationPath': long_str,
            'slave': str(slave.id)
        })

        self.assertEqual(200, api_response.status_code)
        self.assertEqual(
            Status.err({
                "name": [
                    "Ensure this value has at most 200 characters (it has 2000)."
                ],
                "sourcePath": [
                    "Ensure this value has at most 200 characters (it has 2000)."
                ],
                "destinationPath": [
                    "Ensure this value has at most 200 characters (it has 2000)."
                ]
            }),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_add_file_fail_not_unique(self):
        file = FileFactory()

        # add all programs
        api_response = self.client.post(
            '/api/files', {
                'name': file.name,
                'sourcePath': file.sourcePath,
                'destinationPath': file.destinationPath,
                'slave': str(file.slave.id)
            })

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.err({
                'name': ['File with this Name already exists on this Client.']
            }),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_add_file_unsupported_function(self):
        api_response = self.client.delete('/api/files')
        self.assertEqual(api_response.status_code, 403)


class ProgramTests(TestCase):
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

    def test_wol(self):
        #  add a test slave
        slave = SlaveFactory()

        #  non existent slave
        res = self.client.get(
            path=reverse('frontend:wol_slave', args=[999999]))
        self.assertEqual(res.status_code, 500)
        self.assertEqual(res.json()['status'], 'err')
        self.assertEqual(
            res.json()['payload'],
            "DoesNotExist('Slave matching query does not exist.',)",
        )

        #  wrong http method
        res = self.client.post(
            path=reverse('frontend:wol_slave', args=[slave.id]))
        self.assertEqual(res.status_code, 403)

        res = self.client.get(
            path=reverse('frontend:wol_slave', args=[slave.id]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['status'], 'ok')

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
        program = ProgramFactory()
        slave = program.slave
        SlaveStatusFactory(slave=slave, online=True)

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

        self.assertEqual(
            Status.err('Can not start {} because {} is offline!'.format(
                program.name,
                slave.name,
            )),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        self.assertIsNone(client.receive())

    def test_stop_program(self):
        status = ProgramStatusFactory(running=True)
        program = status.program
        slave = program.slave

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
        self.assertEqual(
            Status.err('Can not stop unknown Program'),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_stop_program_stopped_program(self):
        status = ProgramStatusFactory(running=False)
        program = status.program

        api_response = self.client.get(
            reverse(
                'frontend:stop_program',
                args=[program.id],
            ))
        self.assertEqual(200, api_response.status_code)
        self.assertEqual(
            Status.err('Can not stop a not running Program'),
            Status.from_json(api_response.content.decode('utf-8')),
        )


class SlaveTests(TestCase):
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
        slave_status = SlaveStatusFactory(online=True)
        slave = slave_status.slave

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
