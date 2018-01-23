#  pylint: disable=C0111
#  pylint: disable=C0103

from uuid import uuid4
import json
from urllib.parse import urlencode
from shlex import split

from django.test import TestCase
from django.urls import reverse
from channels.test import WSClient

from utils import Status, Command
from frontend.models import (
    Slave as SlaveModel,
    Program as ProgramModel,
    ProgramStatus as ProgramStatusModel,
    SlaveStatus as SlaveStatusModel,
    File as FileModel,
    Script as ScriptModel,
)
from frontend.scripts import Script, ScriptEntryFile, ScriptEntryProgram
from frontend.tests.utils import fill_database_slaves_set_1

class ApiTests(TestCase): # pylint: disable=unused-variable
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
        fill_database_slaves_set_1()
        slave = SlaveModel(
            name="test_slave",
            ip_address="127.0.0.1",
            mac_address="00:00:00:00:00:00",
        )
        slave.save()

        program = ProgramModel(
            name="test_program",
            path="None",
            arguments="None",
            slave=slave,
        )
        program.save()

        file = FileModel(
            name="test_file",
            sourcePath="None",
            destinationPath="None",
            slave=slave,
        )
        file.save()

        script = Script(
            "test_script",
            [ScriptEntryProgram(0, program.id, slave.id)],
            [ScriptEntryFile(0, file.id, slave.id)],
        )
        script.save()

        db_script = ScriptModel.objects.get(name="test_script")

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
        fill_database_slaves_set_1()
        slave = SlaveModel(
            name="test_slave",
            ip_address="127.0.0.1",
            mac_address="00:00:00:00:00:00",
        )
        slave.save()

        program = ProgramModel(
            name="test_program",
            path="None",
            arguments="None",
            slave=slave,
        )
        program.save()

        file = FileModel(
            name="test_file",
            sourcePath="None",
            destinationPath="None",
            slave=slave)
        file.save()

        script = Script(
            "test_script",
            [ScriptEntryProgram(0, program.id, slave.id)],
            [ScriptEntryFile(0, file.id, slave.id)],
        )
        script.save()

        db_script = ScriptModel.objects.get(name="test_script")

        response = self.client.get("/api/script/{}?slaves=int".format(
            db_script.id))

        self.assertEqual(
            Status.ok(dict(script)),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_get_script_program_type_int(self):
        fill_database_slaves_set_1()
        slave = SlaveModel(
            name="test_slave",
            ip_address="127.0.0.1",
            mac_address="00:00:00:00:00:00",
        )
        slave.save()

        program = ProgramModel(
            name="test_program",
            path="None",
            arguments="None",
            slave=slave,
        )
        program.save()

        file = FileModel(
            name="test_file",
            sourcePath="None",
            destinationPath="None",
            slave=slave)
        file.save()

        script = Script(
            "test_script",
            [ScriptEntryProgram(0, program.id, slave.id)],
            [ScriptEntryFile(0, file.id, slave.id)],
        )
        script.save()

        db_script = ScriptModel.objects.get(name="test_script")

        response = self.client.get("/api/script/{}?programs=int".format(
            db_script.id))

        self.assertEqual(
            Status.ok(dict(script)),
            Status.from_json(response.content.decode('utf-8')))

    def test_get_script_slave_program_type_int(self):
        fill_database_slaves_set_1()
        slave = SlaveModel(
            name="test_slave",
            ip_address="127.0.0.1",
            mac_address="00:00:00:00:00:00")
        slave.save()

        program = ProgramModel(
            name="test_program",
            path="None",
            arguments="None",
            slave=slave,
        )
        program.save()

        file = FileModel(
            name="test_file",
            sourcePath="None",
            destinationPath="None",
            slave=slave,
        )
        file.save()

        script = Script(
            "test_script",
            [ScriptEntryProgram(0, program.id, slave.id)],
            [ScriptEntryFile(0, file.id, slave.id)],
        )
        script.save()

        db_script = ScriptModel.objects.get(name="test_script")

        response = self.client.get(
            "/api/script/{}?programs=int&slaves=int".format(db_script.id))

        self.assertEqual(
            Status.ok(dict(script)),
            Status.from_json(response.content.decode('utf-8')))

    def test_get_script_slave_program_type_str(self):
        fill_database_slaves_set_1()
        slave = SlaveModel(
            name="test_slave",
            ip_address="127.0.0.1",
            mac_address="00:00:00:00:00:00")
        slave.save()

        program = ProgramModel(
            name="test_program",
            path="None",
            arguments="None",
            slave=slave,
        )
        program.save()

        file = FileModel(
            name="test_file",
            sourcePath="None",
            destinationPath="None",
            slave=slave,
        )
        file.save()

        script = Script(
            "test_script",
            [ScriptEntryProgram(0, program.id, slave.id)],
            [ScriptEntryFile(0, file.id, slave.id)],
        )
        script.save()

        db_script = ScriptModel.objects.get(name="test_script")

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
        fill_database_slaves_set_1()
        slave = SlaveModel(
            name="test_slave",
            ip_address="127.0.0.1",
            mac_address="00:00:00:00:00:00")
        slave.save()

        program = ProgramModel(
            name="test_program",
            path="None",
            arguments="None",
            slave=slave,
        )
        program.save()

        script = Script(
            "test_script",
            [ScriptEntryProgram(0, program.id, slave.id)],
            [],
        )
        script.save()

        db_script = ScriptModel.objects.get(name="test_script")

        response = self.client.get("/api/script/{}?slaves=str".format(
            db_script.id))

        expected_json = dict(script)
        expected_json['programs'][0]['slave'] = slave.name
        self.assertEqual(
            Status.ok(expected_json),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_get_script_program_type_str(self):
        fill_database_slaves_set_1()
        slave = SlaveModel(
            name="test_slave",
            ip_address="127.0.0.1",
            mac_address="00:00:00:00:00:00",
        )
        slave.save()

        program = ProgramModel(
            name="test_program",
            path="None",
            arguments="None",
            slave=slave,
        )
        program.save()

        script = Script(
            "test_script",
            [ScriptEntryProgram(0, program.id, slave.id)],
            [],
        )
        script.save()

        db_script = ScriptModel.objects.get(name="test_script")

        response = self.client.get("/api/script/{}?programs=str".format(
            db_script.id))

        expected_json = dict(script)
        expected_json['programs'][0]['program'] = program.name
        self.assertEqual(
            Status.ok(expected_json),
            Status.from_json(response.content.decode('utf-8')),
        )

    def test_file_autocomplete(self):
        slave = SlaveModel(
            name="test_slave",
            ip_address="127.0.0.1",
            mac_address="00:00:00:00:00:00",
        )
        slave.save()

        file = FileModel(
            name="test_file",
            sourcePath="None",
            destinationPath="None",
            slave=slave,
        )
        file.save()

        response = self.client.get("/api/files?q=")
        self.assertContains(response, "test_file")
        response = self.client.get("/api/files?q=test")
        self.assertContains(response, "test_file")
        response = self.client.get("/api/files?q=test_")
        self.assertContains(response, "test_file")
        response = self.client.get("/api/files?q=test_file")
        self.assertContains(response, "test_file")
        response = self.client.get("/api/files?q=test_file2")
        self.assertNotContains(response, "test_file")

    def test_program_autocomplete(self):
        slave = SlaveModel(
            name="test_slave",
            ip_address="127.0.0.1",
            mac_address="00:00:00:00:00:00",
        )
        slave.save()

        program = ProgramModel(
            name="test_program",
            path="None",
            arguments="None",
            slave=slave,
        )
        program.save()

        response = self.client.get("/api/programs?q=")
        self.assertContains(response, "test_program")
        response = self.client.get("/api/programs?q=test")
        self.assertContains(response, "test_program")
        response = self.client.get("/api/programs?q=test_")
        self.assertContains(response, "test_program")
        response = self.client.get("/api/programs?q=test_program")
        self.assertContains(response, "test_program")
        response = self.client.get("/api/programs?q=test_program2")
        self.assertNotContains(response, "test_program")

    def test_slave_autocomplete(self):
        slave = SlaveModel(
            name="test_slave",
            ip_address="127.0.0.1",
            mac_address="00:00:00:00:00:00",
        )
        slave.save()

        response = self.client.get("/api/slaves?q=")
        self.assertContains(response, "test_slave")
        response = self.client.get("/api/slaves?q=test")
        self.assertContains(response, "test_slave")
        response = self.client.get("/api/slaves?q=test_")
        self.assertContains(response, "test_slave")
        response = self.client.get("/api/slaves?q=test_slave")
        self.assertContains(response, "test_slave")
        response = self.client.get("/api/slaves?q=test_slave2")
        self.assertNotContains(response, "test_slave")

    def test_add_slave_success(self):
        data_set = [
            SlaveModel(
                name="add_slave_0",
                ip_address="0.0.1.0",
                mac_address="00:00:00:00:01:00",
            ),
            SlaveModel(
                name="add_slave_1",
                ip_address="0.0.1.1",
                mac_address="00:00:00:00:01:01",
            ),
            SlaveModel(
                name="add_slave_2",
                ip_address="0.0.1.2",
                mac_address="00:00:00:00:01:02",
            ),
            SlaveModel(
                name="add_slave_3",
                ip_address="0.0.1.3",
                mac_address="00:00:00:00:01:03",
            ),
        ]

        # make a request for every slave in the data_set
        for data in data_set:
            api_response = self.client.post(
                reverse('frontend:add_slaves'), {
                    'name': data.name,
                    'ip_address': data.ip_address,
                    'mac_address': data.mac_address
                })

            self.assertEqual(api_response.status_code, 200)
            self.assertEqual(
                Status.ok(''),
                Status.from_json(api_response.content.decode('utf-8')),
            )

        # test if all slaves get displayed
        view_response = self.client.get(reverse('frontend:slaves'))
        for data in data_set:
            self.assertContains(view_response, data.name)
            self.assertContains(view_response, data.ip_address)
            self.assertContains(view_response, data.mac_address)

    def test_add_slave_double_entry_fail(self):
        data = SlaveModel(
            name="add_slave_4",
            ip_address="0.0.1.4",
            mac_address="00:00:00:00:01:04",
        )

        # add first slave
        api_response = self.client.post(
            reverse('frontend:add_slaves'), {
                'name': data.name,
                'ip_address': data.ip_address,
                'mac_address': data.mac_address,
            })
        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.ok(''),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        # insert data a second time
        api_response = self.client.post(
            reverse('frontend:add_slaves'), {
                'name': data.name,
                'ip_address': data.ip_address,
                'mac_address': data.mac_address
            })

        # test if the response contains a JSONobject with the error
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
                name=data.name,
                ip_address=data.ip_address,
                mac_address=data.mac_address,
            ).exists())

    def test_add_slave_false_input_fail(self):
        data = SlaveModel(
            name="add_slave_5",
            ip_address="ip address",
            mac_address="mac address",
        )

        api_response = self.client.post(
            reverse('frontend:add_slaves'), {
                'name': data.name,
                'ip_address': data.ip_address,
                'mac_address': data.mac_address
            })
        # test if response was successfull
        self.assertEqual(api_response.status_code, 200)

        # see if message contains the error
        self.assertEqual(
            Status.err({
                "ip_address": ["Enter a valid IPv4 or IPv6 address."],
                "mac_address": ["Enter a valid MAC Address."]
            }), Status.from_json(api_response.content.decode('utf-8')))

        # test if the database does not contain the false slave
        self.assertFalse(
            SlaveModel.objects.filter(
                name=data.name,
                ip_address=data.ip_address,
                mac_address=data.mac_address,
            ).exists())

    def test_add_slave_no_post(self):
        api_response = self.client.put(reverse('frontend:add_slaves'))
        self.assertEqual(api_response.status_code, 403)

    def test_manage_slave_forbidden(self):
        api_response = self.client.get("/api/slave/0")
        self.assertEqual(api_response.status_code, 403)

    def test_remove_slave(self):
        data_set = [
            SlaveModel(
                name="remove_slave_0",
                ip_address="0.0.2.0",
                mac_address="00:00:00:00:02:00",
            ),
            SlaveModel(
                name="remove_slave_1",
                ip_address="0.0.2.1",
                mac_address="00:00:00:00:02:01",
            ),
            SlaveModel(
                name="remove_slave_2",
                ip_address="0.0.2.2",
                mac_address="00:00:00:00:02:02",
            ),
            SlaveModel(
                name="remove_slave_3",
                ip_address="0.0.2.3",
                mac_address="00:00:00:00:02:03",
            ),
        ]

        # make a request for every slave in the data_set
        for data in data_set:
            api_response = self.client.post(
                reverse('frontend:add_slaves'), {
                    'name': data.name,
                    'ip_address': data.ip_address,
                    'mac_address': data.mac_address
                })

            self.assertEqual(api_response.status_code, 200)
            self.assertEqual(
                Status.ok(''),
                Status.from_json(api_response.content.decode('utf-8')),
            )

        # get all the database entries because the ids are needed to delete
        data_in_database_set = []
        for data in data_set:
            data_in_database_set.append(
                SlaveModel.objects.filter(
                    name=data.name,
                    ip_address=data.ip_address,
                    mac_address=data.mac_address,
                ).get())

        # make a request to delete the slave entry
        for data in data_in_database_set:
            api_response = self.client.delete('/api/slave/' + str(data.id))
            self.assertEqual(api_response.status_code, 200)
            self.assertEqual(
                Status.ok(''),
                Status.from_json(api_response.content.decode('utf-8')),
            )
            self.assertFalse(SlaveModel.objects.filter(id=data.id).exists())

    def test_edit_slave(self):
        data_set_1 = [
            SlaveModel(
                name="edit_slave_0",
                ip_address="0.0.3.0",
                mac_address="00:00:00:00:03:00",
            ),
            SlaveModel(
                name="edit_slave_1",
                ip_address="0.0.3.1",
                mac_address="00:00:00:00:03:01",
            ),
            SlaveModel(
                name="edit_slave_2",
                ip_address="0.0.3.2",
                mac_address="00:00:00:00:03:02",
            ),
            SlaveModel(
                name="edit_slave_3",
                ip_address="0.0.3.3",
                mac_address="00:00:00:00:03:03",
            ),
        ]
        data_set_2 = [
            SlaveModel(
                name="edit_slave_4",
                ip_address="0.0.3.4",
                mac_address="00:00:00:00:03:04",
            ),
            SlaveModel(
                name="edit_slave_5",
                ip_address="0.0.3.5",
                mac_address="00:00:00:00:03:05",
            ),
            SlaveModel(
                name="edit_slave_6",
                ip_address="0.0.3.6",
                mac_address="00:00:00:00:03:06",
            ),
            SlaveModel(
                name="edit_slave_7",
                ip_address="0.0.3.7",
                mac_address="00:00:00:00:03:07",
            ),
        ]

        # make a request for every slave in the data_set
        for data in data_set_1:
            api_response = self.client.post(
                reverse('frontend:add_slaves'), {
                    'name': data.name,
                    'ip_address': data.ip_address,
                    'mac_address': data.mac_address
                })
            self.assertEqual(api_response.status_code, 200)
            self.assertEqual(
                Status.ok(''),
                Status.from_json(api_response.content.decode('utf-8')),
            )

        # get all the database entries because the ids are needed to delete
        data_in_database_set = []
        for data in data_set_1:
            data_in_database_set.append(
                SlaveModel.objects.filter(
                    name=data.name,
                    ip_address=data.ip_address,
                    mac_address=data.mac_address,
                ).get())

        # make an edit request for every entry in data_set_1 with the data from dataset 2
        for (data, new_data) in zip(data_in_database_set, data_set_2):
            api_response = self.client.put(
                '/api/slave/' + str(data.id),
                data=urlencode({
                    'name': new_data.name,
                    'ip_address': new_data.ip_address,
                    'mac_address': new_data.mac_address
                }))
            self.assertEqual(api_response.status_code, 200)
            self.assertEqual(
                Status.ok(''),
                Status.from_json(api_response.content.decode('utf-8')),
            )

        # test if the changes have affected the database
        for (data, new_data) in zip(data_set_1, data_set_2):
            self.assertFalse(
                SlaveModel.objects.filter(
                    name=data.name,
                    ip_address=data.ip_address,
                    mac_address=data.mac_address,
                ).exists())
            self.assertTrue(
                SlaveModel.objects.filter(
                    name=new_data.name,
                    ip_address=new_data.ip_address,
                    mac_address=new_data.mac_address,
                ).exists())

    def test_edit_slave_already_exists(self):
        api_response = self.client.post(
            reverse('frontend:add_slaves'), {
                'name': 'edit_slave_fail_0',
                'ip_address': '0.0.4.0',
                'mac_address': '00:00:00:00:04:00'
            })
        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.ok(''),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        api_response = self.client.post(
            reverse('frontend:add_slaves'), {
                'name': 'edit_slave_fail_1',
                'ip_address': '0.0.4.1',
                'mac_address': '00:00:00:00:04:01'
            })
        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.ok(''),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        data = SlaveModel.objects.filter(
            name='edit_slave_fail_0',
            ip_address='0.0.4.0',
            mac_address='00:00:00:00:04:00',
        ).get()
        api_response = self.client.put(
            "/api/slave/" + str(data.id),
            data=urlencode({
                'name': 'edit_slave_fail_1',
                'ip_address': '0.0.4.1',
                'mac_address': '00:00:00:00:04:01'
            }))
        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.err({
                "name": ["Slave with this Name already exists."],
                "ip_address": ["Slave with this Ip address already exists."],
                "mac_address": ["Slave with this Mac address already exists."]
            }), Status.from_json(api_response.content.decode('utf-8')))

    def test_add_program(self):
        SlaveModel(
            name='add_program',
            ip_address='0.0.5.0',
            mac_address='00:00:00:00:04:00',
        ).save()
        model = SlaveModel.objects.get(name='add_program')

        #  add all programs
        for slave_id in range(100):
            api_response = self.client.post(
                '/api/programs', {
                    'name': 'name' + str(slave_id),
                    'path': 'path' + str(slave_id),
                    'arguments': 'arguments' + str(slave_id),
                    'slave': str(model.id),
                    'start_time': -1,
                })
            self.assertEqual(200, api_response.status_code)
            self.assertEqual(
                Status.ok(''),
                Status.from_json(api_response.content.decode('utf-8')),
            )

        # test if all programs are in the database
        for slave_id in range(100):
            self.assertTrue(
                ProgramModel.objects.filter(
                    name='name' + str(slave_id),
                    path='path' + str(slave_id),
                    arguments='arguments' + str(slave_id),
                    slave=model,
                ))

        # delete all entries
        model.delete()

    def test_add_program_fail_length(self):
        SlaveModel(
            name='add_program_fail',
            ip_address='0.0.6.0',
            mac_address='00:00:00:00:06:00',
        ).save()
        model = SlaveModel.objects.get(name='add_program_fail')

        long_str = ''

        for _ in range(2000):
            long_str += 'a'

        api_response = self.client.post(
            '/api/programs', {
                'name': long_str,
                'path': long_str,
                'arguments': long_str,
                'slave': str(model.id),
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

        # delete slave
        model.delete()

    def test_add_program_fail_not_unique(self):
        SlaveModel(
            name='add_program_fail_not_unique',
            ip_address='0.0.6.1',
            mac_address='00:00:00:00:06:01',
        ).save()
        model = SlaveModel.objects.get(name='add_program_fail_not_unique')

        api_response = self.client.post(
            '/api/programs', {
                'name': 'name',
                'path': 'path',
                'arguments': '',
                'slave': str(model.id),
                'start_time': -1,
            })

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.ok(''),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        # try to add program with the same name

        api_response = self.client.post(
            '/api/programs', {
                'name': 'name',
                'path': 'path',
                'arguments': '',
                'slave': str(model.id),
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

        # delete slave
        model.delete()

    def test_add_program_unsupported_function(self):
        SlaveModel(
            name='add_program_unsupported',
            ip_address='0.0.7.0',
            mac_address='00:00:00:00:07:00',
        ).save()
        model = SlaveModel.objects.get(name='add_program_unsupported')

        api_response = self.client.delete('/api/programs')
        self.assertEqual(api_response.status_code, 403)
        SlaveModel.objects.get(
            name='add_program_unsupported',
            ip_address='0.0.7.0',
            mac_address='00:00:00:00:07:00',
        ).delete()

        model.delete()

    #  test wake on lan
    def test_wol(self):
        #  add a test slave
        test_model = SlaveModel(
            name='wol_client',
            ip_address='0.0.5.0',
            mac_address='00:00:00:00:05:00',
        )
        test_model.save()

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
            path=reverse('frontend:wol_slave', args=[test_model.id]))
        self.assertEqual(res.status_code, 403)

        res = self.client.get(
            path=reverse('frontend:wol_slave', args=[test_model.id]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['status'], 'ok')

    def test_remove_program(self):
        slave = SlaveModel(
            name="program_remove_slave_0",
            ip_address="0.0.4.255",
            mac_address="00:00:00:00:04:ff",
        )

        # saving slave in database
        slave.save()

        #  get the database entry for the slave because his id is needed to delete a program
        slave_in_database = SlaveModel.objects.get(name=slave.name)

        data_set = [
            ProgramModel(
                name="problem solver",
                path="/bin/rm",
                arguments="-rf ./*",
                slave=slave_in_database,
            ),
            ProgramModel(
                name="command",
                path="C:\Windows\System32\cmd.exe",
                arguments="",
                slave=slave_in_database,
            ),
            ProgramModel(
                name="browser",
                path="firefox.exe",
                arguments="",
                slave=slave_in_database,
            ),
        ]

        # saving programs in database
        for data in data_set:
            data.save()

        #  get all the database entries because the ids are needed to delete
        data_in_database_set = []
        for data in data_set:
            data_in_database_set.append(
                ProgramModel.objects.get(name=data.name))

        #  make a request to delete the program entry
        for data in data_in_database_set:
            api_response = self.client.delete('/api/program/' + str(data.id))
            self.assertEqual(api_response.status_code, 200)
            self.assertEquals(api_response.json()['status'], 'ok')
            self.assertFalse(ProgramModel.objects.filter(id=data.id).exists())

    def test_manage_program_wrong_http_method(self):
        api_response = self.client.get("/api/program/0")
        self.assertEqual(api_response.status_code, 403)

    def test_modify_program(self):
        # fill database
        SlaveModel(
            name="test_modify_program",
            ip_address='0.0.7.0',
            mac_address='00:00:00:00:07:00',
        ).save()
        slave = SlaveModel.objects.get(
            name="test_modify_program",
            ip_address='0.0.7.0',
            mac_address='00:00:00:00:07:00',
        )

        programs = []
        for i in range(100):
            ProgramModel(
                name="name_" + str(i),
                path="path_" + str(i),
                arguments="arguments_" + str(i),
                slave=slave,
            ).save()
            programs.append(
                ProgramModel.objects.get(
                    name="name_" + str(i),
                    path="path_" + str(i),
                    arguments="arguments_" + str(i),
                    slave=slave,
                ))

        for i in range(100):
            api_response = self.client.put(
                "/api/program/" + str(programs[i].id),
                data=urlencode({
                    'name': str(i),
                    'path': str(i),
                    'arguments': str(i),
                    'slave': str(slave.id),
                    'start_time': -1,
                }))

            self.assertEqual(200, api_response.status_code)
            self.assertEqual(
                Status.ok(''),
                Status.from_json(api_response.content.decode('utf-8')),
            )

        # clear database
        slave.delete()

    def test_modify_program_fail(self):
        # fill database
        SlaveModel(
            name="test_modify_program_fail",
            ip_address='0.0.7.1',
            mac_address='00:00:00:00:07:01',
        ).save()
        slave = SlaveModel.objects.get(
            name="test_modify_program_fail",
            ip_address='0.0.7.1',
            mac_address='00:00:00:00:07:01',
        )

        ProgramModel(name="", path="", arguments="", slave=slave).save()

        program = ProgramModel.objects.get(
            name="", path="", arguments="", slave=slave)

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
        slave.delete()

    def test_edit_program_unique_fail(self):
        # fill database
        SlaveModel(
            name="test_edit_program_unique_fail",
            ip_address='0.0.7.2',
            mac_address='00:00:00:00:07:02',
        ).save()
        slave = SlaveModel.objects.get(
            name="test_edit_program_unique_fail",
            ip_address='0.0.7.2',
            mac_address='00:00:00:00:07:02',
        )

        ProgramModel(
            name="name", path="path", arguments="", slave=slave).save()

        ProgramModel(name="", path="path", arguments="", slave=slave).save()

        program = ProgramModel.objects.get(
            name="",
            path="path",
            arguments="",
            slave=slave,
        )

        api_response = self.client.put(
            "/api/program/" + str(program.id),
            data=urlencode({
                'name': 'name',
                'path': 'path',
                'arguments': '',
                'slave': str(slave.id),
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

        slave.delete()

    def test_execute_program(self):
        SlaveModel(
            name="test_execute_program",
            ip_address='0.0.8.2',
            mac_address='00:00:00:00:08:02',
        ).save()
        slave = SlaveModel.objects.get(
            name="test_execute_program",
            ip_address='0.0.8.2',
            mac_address='00:00:00:00:08:02',
        )

        ProgramModel(
            name="program", path="path", arguments="", slave=slave).save()

        program = ProgramModel.objects.get(
            name="program",
            path="path",
            arguments="",
            slave=slave,
        )

        slave_status = SlaveStatusModel(slave=slave, command_uuid='abcdefg')
        slave_status.online = True
        slave_status.save()

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
        slave.delete()

    def test_execute_program_fail_slave_offline(self):
        SlaveModel(
            name="test_execute_program",
            ip_address='0.0.8.2',
            mac_address='00:00:00:00:08:02',
        ).save()
        slave = SlaveModel.objects.get(
            name="test_execute_program",
            ip_address='0.0.8.2',
            mac_address='00:00:00:00:08:02',
        )

        ProgramModel(
            name="program", path="path", arguments="", slave=slave).save()

        program = ProgramModel.objects.get(
            name="program",
            path="path",
            arguments="",
            slave=slave,
        )

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
        slave.delete()

    def test_shutdown_slave(self):
        SlaveModel(
            name='test_shutdown_slave',
            ip_address='0.0.9.0',
            mac_address='00:00:00:00:09:00',
        ).save()
        slave = SlaveModel.objects.get(name='test_shutdown_slave')

        slave_status = SlaveStatusModel(slave=slave, command_uuid='abc')
        slave_status.online = True
        slave_status.save()

        #  connect slave to websocket
        ws_client = WSClient()
        ws_client.join_group('client_' + str(slave.id))

        #  make request
        api_response = self.client.get(
            path=reverse(
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
            Command.from_json(json.dumps(ws_client.receive())))

        slave.delete()

    def test_shutdown_slave_unknown_slave(self):
        #  make request
        api_response = self.client.get('/api/slave/111/shutdown')
        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.err('Can not shutdown unknown Client'),
            Status.from_json(api_response.content.decode('utf-8')),
        )

    def test_shutdown_slave_offline_slave(self):
        SlaveModel(
            name='test_shutdown_slave_offline_slave',
            ip_address='0.0.9.1',
            mac_address='00:00:00:00:09:01',
        ).save()
        slave = SlaveModel.objects.get(
            name='test_shutdown_slave_offline_slave')

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

        slave.delete()

    def test_shutdown_slave_forbidden_function(self):
        api_response = self.client.delete('/api/slave/1/shutdown')
        self.assertEqual(403, api_response.status_code)

    def test_add_file(self):
        SlaveModel(
            name='add_file',
            ip_address='0.0.5.0',
            mac_address='00:00:00:00:04:00',
        ).save()
        model = SlaveModel.objects.get(name='add_file')

        # add all programs
        for i in range(100):
            api_response = self.client.post(
                '/api/files', {
                    'name': 'name' + str(i),
                    'sourcePath': 'sourcePath' + str(i),
                    'destinationPath': 'destinationPath' + str(i),
                    'slave': str(model.id)
                })
            self.assertEqual(api_response.status_code, 200)
            self.assertEqual(
                Status.ok(''),
                Status.from_json(api_response.content.decode('utf-8')),
            )

        # test if all programs are in the database
        for i in range(100):
            self.assertTrue(
                FileModel.objects.filter(
                    name='name' + str(i),
                    sourcePath='sourcePath' + str(i),
                    destinationPath='destinationPath' + str(i),
                    slave=model,
                ))

        # delete all entries
        model.delete()

    def test_add_file_fail_length(self):
        SlaveModel(
            name='add_file_fail',
            ip_address='0.0.6.0',
            mac_address='00:00:00:00:06:00',
        ).save()
        model = SlaveModel.objects.get(name='add_file_fail')

        long_str = ''

        for _ in range(2000):
            long_str += 'a'

        api_response = self.client.post(
            '/api/files', {
                'name': long_str,
                'sourcePath': long_str,
                'destinationPath': long_str,
                'slave': str(model.id)
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
            }), Status.from_json(api_response.content.decode('utf-8')))

        # delete slave
        model.delete()

    def test_add_file_fail_not_unique(self):
        SlaveModel(
            name='add_file_fail_not_unique',
            ip_address='0.0.6.1',
            mac_address='00:00:00:00:06:01',
        ).save()
        model = SlaveModel.objects.get(name='add_file_fail_not_unique')

        api_response = self.client.post(
            '/api/files', {
                'name': 'name',
                'sourcePath': 'sourcePath',
                'destinationPath': 'destinationPath',
                'slave': str(model.id),
            })

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.ok(''),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        # try to add program with the same name
        api_response = self.client.post(
            '/api/files', {
                'name': 'name',
                'sourcePath': 'sourcePath',
                'destinationPath': 'destinationPath',
                'slave': str(model.id),
            })

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            Status.err({
                'name': ['File with this Name already exists on this Client.']
            }),
            Status.from_json(api_response.content.decode('utf-8')),
        )

        # delete slave
        model.delete()

    def test_add_file_unsupported_function(self):
        SlaveModel(
            name='add_file_unsupported',
            ip_address='0.0.7.0',
            mac_address='00:00:00:00:07:00',
        ).save()
        model = SlaveModel.objects.get(name='add_file_unsupported')

        api_response = self.client.delete('/api/files')
        self.assertEqual(api_response.status_code, 403)
        SlaveModel.objects.get(
            name='add_file_unsupported',
            ip_address='0.0.7.0',
            mac_address='00:00:00:00:07:00',
        ).delete()

        model.delete()

    def test_stop_program(self):
        SlaveModel(
            name='stop_program',
            ip_address='0.0.13.0',
            mac_address='00:00:00:00:07:00').save()
        slave = SlaveModel.objects.get(name='stop_program')
        ProgramModel(
            name='program',
            path='path',
            arguments='args',
            slave=slave,
        ).save()
        program = ProgramModel.objects.get(name='program', slave=slave)
        cmd_uuid = uuid4()
        ProgramStatusModel(
            program=program,
            running=True,
            command_uuid=cmd_uuid,
        ).save()

        slave_ws = WSClient()
        slave_ws.join_group('client_' + str(slave.id))

        # test api
        api_response = self.client.get(
            path=reverse(
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
            Command(method='execute', uuid=cmd_uuid),
            Command.from_json(json.dumps(slave_ws.receive())),
        )

        slave.delete()

    def test_stop_program_unknown_request(self):
        api_request = self.client.post(
            reverse('frontend:stop_program', args=[0]))
        self.assertEqual(403, api_request.status_code)

    def test_stop_program_unknown_program(self):
        api_response = self.client.get(
            reverse('frontend:stop_program', args=[9999]))
        self.assertEqual(200, api_response.status_code)
        self.assertEqual(
            Status.err('Can not stop unknown Program'),
            Status.from_json(api_response.content.decode('utf-8')))

    def test_stop_program_stopped_program(self):
        SlaveModel(
            name='stop_program_stopped_program',
            ip_address='0.0.13.1',
            mac_address='00:00:00:00:07:01').save()
        slave = SlaveModel.objects.get(name='stop_program_stopped_program')
        ProgramModel(
            name='program', path='path', arguments='args', slave=slave).save()
        program = ProgramModel.objects.get(name='program', slave=slave)
        ProgramStatusModel(
            program=program, running=False, command_uuid=uuid4()).save()

        api_response = self.client.get(
            reverse('frontend:stop_program', args=[program.id]))
        self.assertEqual(200, api_response.status_code)
        self.assertEqual(
            Status.err('Can not stop a not running Program'),
            Status.from_json(api_response.content.decode('utf-8')))
