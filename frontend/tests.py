#  pylint: disable=C0111
#  pylint: disable=C0103

from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from urllib.parse import urlencode
from utils import Status, Command
from shlex import split
from datetime import datetime
from uuid import uuid4

from channels.test import WSClient
from channels import Group

import json

from .models import (
    Slave as SlaveModel,
    validate_mac_address,
    Program as ProgramModel,
    SlaveStatus as SlaveStatusModel,
    ProgramStatus as ProgramStatusModel,
    ScriptGraphPrograms as SGP,
    ScriptGraphFiles as SGF,
    Script as ScriptModel,
    File as FileModel,
)

from .scripts import Script, ScriptEntryFile, ScriptEntryProgram


def fill_database_slaves_set_1():
    data_set = [
        SlaveModel(
            name="Slave1",
            ip_address="192.168.2.39",
            mac_address="00:00:00:00:00:01",
        ),
        SlaveModel(
            name="Slave2",
            ip_address="192.168.3.39",
            mac_address="02:00:00:00:00:00",
        ),
        SlaveModel(
            name="Slave3",
            ip_address="192.168.5.39",
            mac_address="00:02:00:00:00:00",
        ),
        SlaveModel(
            name="Slave4",
            ip_address="192.168.6.39",
            mac_address="00:00:02:00:00:00",
        ),
        SlaveModel(
            name="Slave5",
            ip_address="192.168.7.39",
            mac_address="00:00:00:02:00:00",
        )
    ]

    for data in data_set:
        data.save()

    return data_set


class FrontendTests(TestCase):
    def test_welcome_get(self):
        response = self.client.get(reverse('frontend:welcome'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "welcome")

    def test_script_delete(self):
        slave = SlaveModel(
            name="test_slave",
            ip_address="0.0.0.0",
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
            slave=slave)
        file.save()

        script = Script(
            "test_script",
            [ScriptEntryProgram(0, "test_program", "test_slave")],
            [ScriptEntryFile(0, "test_file", "test_slave")],
        )
        script.save()

        db_script = ScriptModel.objects.get(name="test_script")

        response = self.client.delete("/api/script/" + str(db_script.id))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            ScriptModel.objects.filter(name="test_script").exists())

    def test_slave_get(self):
        data_set = fill_database_slaves_set_1()

        response = self.client.get(reverse('frontend:slaves'))
        self.assertEqual(response.status_code, 200)

        for data in data_set:
            self.assertContains(response, data.name)
            self.assertContains(response, data.mac_address)
            self.assertContains(response, data.ip_address)

    def test_scripts_get(self):
        response = self.client.get(reverse('frontend:scripts'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Scripts")


class ApiTests(TestCase):
    def test_get_script(self):
        fill_database_slaves_set_1()
        slave = SlaveModel(
            name="test_slave",
            ip_address="0.0.0.0",
            mac_address="00:00:00:00:00:00")
        slave.save()

        program = ProgramModel(
            name="test_program", path="None", arguments="None", slave=slave)
        program.save()

        file = FileModel(
            name="test_file",
            sourcePath="None",
            destinationPath="None",
            slave=slave)
        file.save()

        script = Script("test_script",
                        [ScriptEntryProgram(0, program.id, slave.id)],
                        [ScriptEntryFile(0, file.id, slave.id)])
        script.save()

        db_script = ScriptModel.objects.get(name="test_script")

        response = self.client.get("/api/script/{}".format(db_script.id))

        self.assertEqual(
            Status.ok(dict(script)),
            Status.from_json(response.content.decode('utf-8')))

    def test_script_wrong_type_slaves(self):
        response = self.client.get("/api/script/0?slaves=float")
        self.assertContains(response, "err")
        self.assertContains(response,
                            "slaves only allow str or int. (given float)")

    def test_script_wrong_type_programs(self):
        response = self.client.get("/api/script/0?programs=float")
        self.assertContains(response, "err")
        self.assertContains(response,
                            "programs only allow str or int. (given float)")

    def test_script_wrong_type_files(self):
        response = self.client.get("/api/script/0?files=float")
        self.assertContains(response, "err")
        self.assertContains(response,
                            "files only allow str or int. (given float)")

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
            ip_address="0.0.0.0",
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
            ip_address="0.0.0.0",
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
            ip_address="0.0.0.0",
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
            ip_address="0.0.0.0",
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
            ip_address="0.0.0.0",
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
            ip_address="0.0.0.0",
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
            ip_address="0.0.0.0",
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
            ip_address="0.0.0.0",
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
            ip_address="0.0.0.0",
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
                    "Ensure this value has at most 200 characters (it has 2000)."
                ],
                "path": [
                    "Ensure this value has at most 200 characters (it has 2000)."
                ],
                "arguments": [
                    "Ensure this value has at most 200 characters (it has 2000)."
                ]
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
                    "Ensure this value has at most 200 characters (it has 2000)."
                ],
                "path": [
                    "Ensure this value has at most 200 characters (it has 2000)."
                ],
                "arguments": [
                    "Ensure this value has at most 200 characters (it has 2000)."
                ]
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
            name='program', path='path', arguments='args', slave=slave).save()
        program = ProgramModel.objects.get(name='program', slave=slave)
        cmd_uuid = uuid4()
        ProgramStatusModel(
            program=program, running=True, command_uuid=cmd_uuid).save()

        slave_ws = WSClient()
        slave_ws.join_group('client_' + str(slave.id))

        # test api
        api_response = self.client.get(
            path=reverse('frontend:stop_program', args=[program.id]))
        self.assertEqual(200, api_response.status_code)
        self.assertEqual(
            Status.ok(''),
            Status.from_json(api_response.content.decode('utf-8')))

        # test message
        self.assertEqual(
            Command(method='execute', uuid=cmd_uuid),
            Command.from_json(json.dumps(slave_ws.receive())))

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


class WebsocketTests(TestCase):
    def test_rpc_commands_fails_unkown_slave(self):
        ws_client = WSClient()
        self.assertRaisesMessage(
            AssertionError,
            "Connection rejected: {'accept': False} != '{accept: True}'",
            ws_client.send_and_consume,
            "websocket.connect",
            path="/commands",
            content={'client': ['0.0.9.0', '00:00:00:00:09:00']},
        )

    def test_rpc_commands(self):
        SlaveModel(
            name="test_rpc_commands",
            ip_address='0.0.10.0',
            mac_address='00:00:00:00:10:00',
        ).save()
        slave = SlaveModel.objects.get(
            name="test_rpc_commands",
            ip_address='0.0.10.0',
            mac_address='00:00:00:00:10:00',
        )

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.connect',
            path='/commands',
            content={'client': ['0.0.10.0', '00:00:00:00:10:00']},
        )

        self.assertEqual(
            Command(method="online"),
            Command.from_json(json.dumps(ws_client.receive())),
        )

        #  test if the client is now part of the right groups
        Group('clients').send({'text': 'ok'}, immediately=True)
        self.assertEqual(ws_client.receive(json=False), 'ok')

        Group('client_{}'.format(slave.id)).send(
            {
                'text': 'ok'
            },
            immediately=True,
        )
        self.assertEqual(ws_client.receive(json=False), 'ok')

        slave.delete()

    def test_ws_rpc_disconnect(self):
        SlaveModel(
            name="test_ws_rpc_disconnect",
            ip_address='0.0.10.1',
            mac_address='00:00:00:00:10:01',
        ).save()

        slave = SlaveModel.objects.get(
            name="test_ws_rpc_disconnect",
            ip_address='0.0.10.1',
            mac_address='00:00:00:00:10:01',
        )

        SlaveStatusModel(slave=slave, command_uuid='abcdefg').save()
        slave_status = SlaveStatusModel.objects.get(slave=slave)
        slave_status.online = True
        slave_status.save()

        #  register program
        ProgramModel(
            slave=slave,
            name='name',
            path='path',
            arguments='',
        ).save()
        program = ProgramModel.objects.get(slave=slave)
        ProgramStatusModel(program=program, command_uuid='abcdefg').save()

        # connect client on /commands
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.connect',
            path='/commands',
            content={
                'client': ['0.0.10.1', '00:00:00:00:10:01']
            })

        # connect webinterface on /notifications
        webinterface = WSClient()
        webinterface.send_and_consume(
            'websocket.connect',
            path='/notifications',
        )

        #  throw away connect repsonse
        ws_client.receive()

        ws_client.send_and_consume('websocket.disconnect', path='/commands')

        #  test if SlaveStatus was to offline
        self.assertFalse(SlaveStatusModel.objects.get(slave=slave).online)

        #  test if the client was removed from the correct groups
        Group('clients').send({'text': 'ok'}, immediately=True)
        self.assertIsNone(ws_client.receive())

        Group('client_{}'.format(slave.id)).send(
            {
                'text': 'ok'
            },
            immediately=True,
        )
        self.assertIsNone(ws_client.receive())

        #  test if program status was removed
        self.assertFalse(
            ProgramStatusModel.objects.filter(program=program).exists())

        #  test if a "disconnected" message has been send to the webinterface
        self.assertEqual(
            Status.ok({
                'slave_status': 'disconnected',
                'sid': str(slave.id)
            }), Status.from_json(json.dumps(webinterface.receive())))

        slave.delete()

    def test_ws_notifications_connect_and_ws_disconnect(self):
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.connect',
            path='/notifications',
        )

        #  test if ws_client is part of 'notifications'
        Group('notifications').send({'text': Status.ok('').to_json()})
        self.assertEqual(
            Status.ok(''),
            Status.from_json(json.dumps(ws_client.receive())),
        )

        ws_client.send_and_consume(
            'websocket.disconnect',
            path='/notifications',
        )

        #  test if ws_client was removed from 'notifications'
        Group('notifications').send({'text': Status.ok('').to_json()})
        self.assertIsNone(ws_client.receive())

    def test_ws_notifications_receive_fail(self):
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/notifications',
        )
        self.assertIsNone(ws_client.receive())

    def test_ws_notifications_receive_online(self):
        SlaveModel(
            name="test_ws_notifications_receive_online",
            ip_address='0.0.10.2',
            mac_address='00:00:00:00:10:02',
        ).save()
        slave = SlaveModel.objects.get(
            name="test_ws_notifications_receive_online",
            ip_address='0.0.10.2',
            mac_address='00:00:00:00:10:02',
        )

        uuid = uuid4().hex
        SlaveStatusModel(slave=slave, command_uuid=uuid).save()
        expected_status = Status.ok({'method': 'online'})
        expected_status.uuid = uuid

        # connect webinterface on /notifications
        webinterface = WSClient()
        webinterface.join_group('notifications')

        # send online answer
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/notifications',
            content={'text': expected_status.to_json()},
        )

        self.assertTrue(SlaveStatusModel.objects.get(slave=slave).online)

        # test if a connected message was send on /notifications
        self.assertEqual(
            Status.ok({
                'slave_status': 'connected',
                'sid': str(slave.id),
            }),
            Status.from_json(json.dumps(webinterface.receive())),
        )

        slave.delete()

    def test_ws_notifications_receive_online_status_err(self):
        SlaveModel(
            name="test_ws_notifications_receive_online_status_err",
            ip_address='0.0.10.15',
            mac_address='00:00:00:00:10:15',
        ).save()
        slave = SlaveModel.objects.get(
            name="test_ws_notifications_receive_online_status_err",
            ip_address='0.0.10.15',
            mac_address='00:00:00:00:10:15',
        )

        uuid = uuid4().hex
        SlaveStatusModel(slave=slave, command_uuid=uuid).save()
        error_status = Status.err({
            'method': 'online',
            'result': str(Exception('foobar'))
        })
        error_status.uuid = uuid

        # connect webinterface on /notifications
        webinterface = WSClient()
        webinterface.join_group('notifications')

        # send online answer
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/notifications',
            content={
                'text': error_status.to_json()
            })

        self.assertFalse(SlaveStatusModel.objects.get(slave=slave).online)

        # test if a connected message was send on /notifications
        self.assertEqual(
            Status.err(
                'An error occurred while connecting to client {}!'.format(
                    slave.name)),
            Status.from_json(json.dumps(webinterface.receive())),
        )

        slave.delete()

    def test_ws_notifications_receive_execute(self):
        SlaveModel(
            name="test_ws_notifications_receive_execute",
            ip_address='0.0.10.3',
            mac_address='00:00:00:00:10:03',
        ).save()
        slave = SlaveModel.objects.get(
            name="test_ws_notifications_receive_execute",
            ip_address='0.0.10.3',
            mac_address='00:00:00:00:10:03',
        )

        ProgramModel(
            name='program', path='path', arguments='', slave=slave).save()

        program = ProgramModel.objects.get(
            name='program',
            path='path',
            arguments='',
            slave=slave,
        )

        uuid = uuid4().hex
        program_status = ProgramStatusModel(program=program, command_uuid=uuid)
        program_status.running = True
        program_status.save()

        expected_status = Status.ok({'method': 'execute', 'result': 0})
        expected_status.uuid = uuid

        #  connect webinterface
        webinterface = WSClient()
        webinterface.send_and_consume(
            'websocket.connect',
            path='/notifications',
        )

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/notifications',
            content={'text': expected_status.to_json()},
        )

        query = ProgramStatusModel.objects.filter(program=program, code=0)
        self.assertTrue(query.count() == 1)
        self.assertFalse(query.first().running)

        #  test if the webinterface gets the "finished" message
        self.assertEqual(
            Status.ok({
                'program_status': 'finished',
                'pid': str(program.id),
                'code': 0,
            }),
            Status.from_json(json.dumps(webinterface.receive())),
        )

        slave.delete()

    def test_ws_notifications_receive_execute_status_err(self):
        SlaveModel(
            name="test_ws_notifications_receive_execute_status_err",
            ip_address='0.0.10.33',
            mac_address='00:00:00:00:10:33').save()
        slave = SlaveModel.objects.get(
            name="test_ws_notifications_receive_execute_status_err",
            ip_address='0.0.10.33',
            mac_address='00:00:00:00:10:33')

        ProgramModel(
            name='program',
            path='path',
            arguments='',
            slave=slave,
        ).save()

        program = ProgramModel.objects.get(
            name='program',
            path='path',
            arguments='',
            slave=slave,
        )

        uuid = uuid4().hex
        program_status = ProgramStatusModel(program=program, command_uuid=uuid)
        program_status.running = True
        program_status.save()

        error_status = Status.err({
            'method': 'execute',
            'result': str(Exception('foobar')),
        })
        error_status.uuid = uuid

        #  connect webinterface
        webinterface = WSClient()
        webinterface.join_group('notifications')

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/notifications',
            content={'text': error_status.to_json()},
        )

        query = ProgramStatusModel.objects.get(program=program)
        self.assertFalse(query.running)
        self.assertEqual(query.code, 'foobar')

        #  test if the webinterface gets the error message
        self.assertEqual(
            Status.err(
                'An Exception occurred while trying to execute {}'.format(
                    program.name)),
            Status.from_json(json.dumps(webinterface.receive())),
        )

        slave.delete()

    def test_ws_notifications_receive_unknown_method(self):
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/notifications',
            content={'text': Status.ok({
                'method': ''
            }).to_json()},
        )

        self.assertIsNone(ws_client.receive())


class DatabaseTests(TestCase):
    def test_slave_has_err(self):
        slave = SlaveModel(
            name="test_slave",
            ip_address="192.168.5.0",
            mac_address="00:02:00:00:00:00",
        )

        slave.save()

        prog = ProgramModel(slave=slave, name="test_prog", path="None")
        prog.save()

        self.assertFalse(slave.has_error)
        self.assertFalse(slave.has_running)

    def test_slave_is_online_err(self):
        slave = SlaveModel(
            name="test_slave",
            ip_address="192.168.5.0",
            mac_address="00:02:00:00:00:00",
        )

        slave.save()

        self.assertFalse(slave.is_online)

    def test_program_is_err(self):
        slave = SlaveModel(
            name="test_slave",
            ip_address="192.168.5.0",
            mac_address="00:02:00:00:00:00",
        )

        slave.save()

        prog = ProgramModel(slave=slave, name="test_prog", path="None")
        prog.save()

        self.assertFalse(prog.is_running)
        self.assertFalse(prog.is_error)
        self.assertFalse(prog.is_successful)
        self.assertFalse(prog.is_executed)

    def test_slave_insert_valid(self):
        mod = SlaveModel(
            name="Tommo3",
            ip_address="192.168.5.39",
            mac_address="00:02:00:00:00:00",
        )
        mod.full_clean()
        mod.save()
        self.assertTrue(SlaveModel.objects.filter(name="Tommo3").exists())

    def test_program_running(self):
        slave = SlaveModel(
            name="test_slave",
            ip_address="0.0.2.0",
            mac_address="00:00:00:00:00:00",
        )
        slave.save()

        prog = ProgramModel(name="test_program", path="none", slave=slave)
        prog.save()

        ProgramStatusModel(
            command_uuid=uuid4(),
            code="",
            program=prog,
            running=True,
        ).save()

        self.assertTrue(slave.has_running)
        self.assertFalse(slave.has_error)
        self.assertTrue(prog.is_running)
        self.assertFalse(prog.is_executed)
        self.assertFalse(prog.is_successful)
        self.assertFalse(prog.is_error)

    def test_program_successful(self):
        slave = SlaveModel(
            name="test_slave",
            ip_address="0.0.2.0",
            mac_address="00:00:00:00:00:00",
        )
        slave.save()

        prog = ProgramModel(name="test_program", path="none", slave=slave)
        prog.save()

        ProgramStatusModel(
            command_uuid=uuid4(),
            code="0",
            program=prog,
            running=False,
        ).save()

        self.assertFalse(slave.has_running)
        self.assertFalse(slave.has_error)
        self.assertFalse(prog.is_running)
        self.assertTrue(prog.is_executed)
        self.assertTrue(prog.is_successful)
        self.assertFalse(prog.is_error)

    def test_program_error(self):
        slave = SlaveModel(
            name="test_slave",
            ip_address="0.0.2.0",
            mac_address="00:00:00:00:00:00",
        )
        slave.save()

        prog = ProgramModel(name="test_program", path="none", slave=slave)
        prog.save()

        ProgramStatusModel(
            command_uuid=uuid4(),
            code="1",
            program=prog,
            running=False,
        ).save()

        self.assertFalse(slave.has_running)
        self.assertTrue(slave.has_error)
        self.assertFalse(prog.is_running)
        self.assertTrue(prog.is_executed)
        self.assertFalse(prog.is_successful)
        self.assertTrue(prog.is_error)

    def test_flush_error(self):
        from .apps import flush
        SlaveModel(
            name='test_flush_error',
            ip_address='0.1.0.0',
            mac_address='00:01:00:00:00:00',
        ).save()
        flush('Slave')
        flush('UnknownModel')
        self.assertFalse(
            SlaveModel.objects.filter(name='test_flush_error').exists())

    def test_slave_insert_invalid_ip(self):
        self.assertRaises(
            ValidationError, SlaveModel(ip_address='my_cool_ip').full_clean)

    def test_slave_insert_invalid_mac(self):
        self.assertRaises(
            ValidationError, SlaveModel(mac_address='my_cool_mac').full_clean)

    def test_mac_validator_upper(self):
        validate_mac_address("00:AA:BB:CC:DD:EE")
        self.assertTrue(True)

    def test_mac_validator_lower(self):
        validate_mac_address("00:aa:bb:cc:dd:ee")
        self.assertTrue(True)

    def test_mac_validator_mixed(self):
        validate_mac_address("00:Aa:Bb:cC:dD:EE")
        self.assertTrue(True)

    def test_mac_validator_too_short(self):
        self.assertRaises(
            ValidationError,
            validate_mac_address,
            "00:02:23",
        )

    def test_mac_validator_too_long(self):
        self.assertRaises(
            ValidationError,
            validate_mac_address,
            "00:02:23:23:23:23:32",
        )

    def test_mac_validator_too_long_inner(self):
        self.assertRaises(
            ValidationError,
            validate_mac_address,
            "00:02:23:223:23:23",
        )

    def test_mac_validator_too_short_inner(self):
        self.assertRaises(
            ValidationError,
            validate_mac_address,
            "00:02:23:2:23:23",
        )

    def test_flush(self):
        slave = SlaveModel(
            name="test",
            ip_address="127.0.0.1",
            mac_address="00:00:00:00:00:00",
        )
        slave.save()

        prog = ProgramModel(
            name="test",
            path="None",
            arguments="None",
            slave=slave,
        )
        prog.save()

        status_slave = SlaveStatusModel(slave=slave, command_uuid='abc')
        status_slave.save()

        status_program = ProgramStatusModel(prog.id, "None", datetime.now())
        status_program.save()

        self.assertEqual(SlaveStatusModel.objects.count(), 1)
        self.assertEqual(ProgramStatusModel.objects.count(), 1)

        from .apps import flush
        flush("SlaveStatus", "ProgramStatus")

        self.assertEqual(SlaveStatusModel.objects.count(), 0)
        self.assertEqual(ProgramStatusModel.objects.count(), 0)


class ComponentTests(TestCase):
    def test_script_entry(self):
        from .templatetags.components import script_entry
        response = script_entry("test")
        self.assertEqual({"script": "test"}, response)


class ScriptTests(TestCase):
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
        self.assertRaises(ValueError, ScriptEntryProgram, "a name", "whoops",
                          0)

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

        script = Script("test", [ScriptEntryProgram(0, "no name", 0)],
                        [ScriptEntryFile(0, "no name", 0)])

        self.assertEqual(Script.from_json(string), script)
        self.assertEqual(Script.from_json(script.to_json()), script)

    def test_script_entry_program_json(self):
        string = '{"index": 0, "slave": 0, "program": "no name"}'

        script = ScriptEntryProgram(0, "no name", 0)

        self.assertEqual(ScriptEntryProgram.from_json(string), script)
        self.assertEqual(
            ScriptEntryProgram.from_json(script.to_json()), script)

    def test_script_entry_file_json(self):
        string = '{"index": 0, "slave": 0, "file": "no name"}'

        script = ScriptEntryFile(0, "no name", 0)

        self.assertEqual(ScriptEntryFile.from_json(string), script)
        self.assertEqual(ScriptEntryFile.from_json(script.to_json()), script)

    def test_script_name_eq(self):
        self.assertNotEqual(Script("test", [], []), Script("test2", [], []))

    def test_model_support_strings(self):
        slave = SlaveModel(
            name="test_slave",
            ip_address="0.0.0.0",
            mac_address="00:00:00:00:00:00")
        slave.save()

        program = ProgramModel(
            name="test_program", path="None", arguments="None", slave=slave)
        program.save()

        file = FileModel(
            name="test_file",
            sourcePath="None",
            destinationPath="None",
            slave=slave)
        file.save()

        script = Script("test_script",
                        [ScriptEntryProgram(0, "test_program", "test_slave")],
                        [ScriptEntryFile(0, "test_file", "test_slave")])
        script.save()

        self.assertTrue(
            ScriptModel.objects.filter(name="test_script").exists())
        self.assertTrue(
            SGP.objects.filter(
                script=ScriptModel.objects.get(name="test_script"),
                index=0,
                program=program).exists())

        self.assertTrue(
            SGF.objects.filter(
                script=ScriptModel.objects.get(name="test_script"),
                index=0,
                file=file).exists())

    def test_model_support_ids(self):
        slave = SlaveModel(
            name="test_slave",
            ip_address="0.0.0.0",
            mac_address="00:00:00:00:00:00")
        slave.save()

        program = ProgramModel(
            name="test_program", path="None", arguments="None", slave=slave)
        program.save()

        script = Script("test_script",
                        [ScriptEntryProgram(0, program.id, slave.id)], [])
        script.save()

        self.assertTrue(
            ScriptModel.objects.filter(name="test_script").exists())
        self.assertTrue(
            SGP.objects.filter(
                script=ScriptModel.objects.get(name="test_script"),
                index=0,
                program=program).exists())

    def test_model_support_error_in_entry(self):

        slave = SlaveModel(
            name="test_slave",
            ip_address="0.0.0.0",
            mac_address="00:00:00:00:00:00")
        slave.save()

        program = ProgramModel(
            name="test_program", path="None", arguments="None", slave=slave)
        program.save()

        script = Script(
            "test_scripts",
            [
                ScriptEntryProgram(0, program.id, slave.id),
                ScriptEntryProgram(0, program.id + 1, slave.id),
            ],
            [],
        )

        self.assertRaises(ProgramModel.DoesNotExist, script.save)
        self.assertTrue(
            not ScriptModel.objects.filter(name="test_script").exists())
        self.assertTrue(len(SGP.objects.all()) == 0)

    def test_from_model_file_id_eq_str(self):
        from django.db.utils import IntegrityError
        slave = SlaveModel(
            name="test_slave",
            ip_address="0.0.0.0",
            mac_address="00:00:00:00:00:00")
        slave.save()

        file = FileModel(
            name="test_file",
            sourcePath="None",
            destinationPath="None",
            slave=slave)
        file.save()

        script = ScriptModel(name="test_script")
        script.save()

        a = ScriptEntryFile(0, file.id, slave.id).as_model(script)
        b = ScriptEntryFile(0, file.name, slave.name).as_model(script)
        a.save()
        self.assertRaises(IntegrityError, b.save)

    def test_from_model_program_id_eq_str(self):
        from django.db.utils import IntegrityError
        slave = SlaveModel(
            name="test_slave",
            ip_address="0.0.0.0",
            mac_address="00:00:00:00:00:00")
        slave.save()

        program = ProgramModel(
            name="test_program", path="None", arguments="None", slave=slave)
        program.save()

        script = ScriptModel(name="test_script")
        script.save()

        with_int = ScriptEntryProgram(0, program.id, slave.id).as_model(script)
        with_str = ScriptEntryProgram(0, program.name,
                                      slave.name).as_model(script)
        with_int.save()
        self.assertRaises(IntegrityError, with_str.save)

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
        self.assertRaises(ValueError, ScriptEntryProgram.from_query, Dummy(),
                          "int", "not str")

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
        from .scripts import get_slave
        self.assertEqual(None, get_slave(None))
