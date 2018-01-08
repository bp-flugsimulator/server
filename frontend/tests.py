from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from urllib.parse import urlencode
from utils import Status, Command
from shlex import split
from django.utils import timezone
from datetime import datetime

from channels.test import WSClient
from channels import Group

import json

from .models import Slave as SlaveModel, validate_mac_address, Program as ProgramModel, SlaveStatus as SlaveStatusModel, ProgramStatus as ProgramStatusModel, ScriptGraphPrograms as SGP, ScriptGraphFiles as SGF, Script as ScriptModel, File as FileModel
from .consumers import ws_rpc_connect
from .scripts import Script, ScriptEntryFile, ScriptEntryProgram


def fill_database_slaves_set_1():
    data_set = [
        SlaveModel(
            name="Tommo1",
            ip_address="192.168.2.39",
            mac_address="00:00:00:00:00:01",
        ),
        SlaveModel(
            name="Tommo2",
            ip_address="192.168.3.39",
            mac_address="02:00:00:00:00:00",
        ),
        SlaveModel(
            name="Tommo3",
            ip_address="192.168.5.39",
            mac_address="00:02:00:00:00:00",
        ),
        SlaveModel(
            name="Tommo4",
            ip_address="192.168.6.39",
            mac_address="00:00:02:00:00:00",
        ),
        SlaveModel(
            name="Tommo5",
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

    def test_script_get(self):
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

        db_script = ScriptModel.objects.get(name="test_script")

        response = self.client.get("/script/" + str(db_script.id))
        self.assertEqual(response.status_code, 200)


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

        self.assertContains(response, "ok")
        self.assertContains(response, "test_script")
        self.assertContains(response, "program")
        self.assertContains(response, 0)
        self.assertContains(response, program.id)
        self.assertContains(response, slave.id)
        self.assertContains(response, file.id)
        self.assertNotContains(response, program.name)
        self.assertNotContains(response, slave.name)
        self.assertNotContains(response, file.name)

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

        response = self.client.get("/api/script/{}?slaves=int".format(
            db_script.id))

        self.assertContains(response, "ok")
        self.assertContains(response, "test_script")
        self.assertContains(response, "program")
        self.assertContains(response, 0)
        self.assertContains(response, program.id)
        self.assertContains(response, slave.id)
        self.assertContains(response, file.id)
        self.assertNotContains(response, program.name)
        self.assertNotContains(response, slave.name)
        self.assertNotContains(response, file.name)

    def test_get_script_program_type_int(self):
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

        response = self.client.get("/api/script/{}?programs=int".format(
            db_script.id))

        self.assertContains(response, "ok")
        self.assertContains(response, "test_script")
        self.assertContains(response, "program")
        self.assertContains(response, 0)
        self.assertContains(response, program.id)
        self.assertContains(response, slave.id)
        self.assertContains(response, file.id)
        self.assertNotContains(response, program.name)
        self.assertNotContains(response, slave.name)
        self.assertNotContains(response, file.name)

    def test_get_script_slave_program_type_int(self):
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

        response = self.client.get(
            "/api/script/{}?programs=int&slaves=int".format(db_script.id))

        self.assertContains(response, "ok")
        self.assertContains(response, "test_script")
        self.assertContains(response, "program")
        self.assertContains(response, 0)
        self.assertContains(response, program.id)
        self.assertContains(response, slave.id)
        self.assertContains(response, file.id)
        self.assertNotContains(response, program.name)
        self.assertNotContains(response, slave.name)
        self.assertNotContains(response, file.name)

    def test_get_script_slave_program_type_str(self):
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

        response = self.client.get(
            "/api/script/{}?programs=str&slaves=str&files=str".format(
                db_script.id))

        self.assertContains(response, "ok")
        self.assertContains(response, "test_script")
        self.assertContains(response, "program")
        self.assertContains(response, 0)
        self.assertContains(response, program.name)
        self.assertContains(response, slave.name)
        self.assertContains(response, file.name)
        self.assertNotContains(response, program.id)
        self.assertNotContains(response, slave.id)
        self.assertNotContains(response, file.id)

    def test_get_script_slave_type_str(self):
        fill_database_slaves_set_1()
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

        db_script = ScriptModel.objects.get(name="test_script")

        response = self.client.get("/api/script/{}?slaves=str".format(
            db_script.id))

        self.assertContains(response, "ok")
        self.assertContains(response, "test_script")
        self.assertContains(response, "program")
        self.assertContains(response, 0)
        self.assertContains(response, program.id)
        self.assertContains(response, slave.name)
        self.assertNotContains(response, program.name)
        self.assertNotContains(response, slave.id)

    def test_get_script_program_type_str(self):
        fill_database_slaves_set_1()
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

        db_script = ScriptModel.objects.get(name="test_script")

        response = self.client.get("/api/script/{}?programs=str".format(
            db_script.id))

        self.assertContains(response, "ok")
        self.assertContains(response, "test_script")
        self.assertContains(response, "program")
        self.assertContains(response, 0)
        self.assertContains(response, program.name)
        self.assertContains(response, slave.id)
        self.assertNotContains(response, program.id)
        self.assertNotContains(response, slave.name)

    def test_file_autocomplete(self):
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
            mac_address="00:00:00:00:00:00")
        slave.save()

        program = ProgramModel(
            name="test_program", path="None", arguments="None", slave=slave)
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
            mac_address="00:00:00:00:00:00")
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

        #make a request for every slave in the data_set
        for data in data_set:
            api_response = self.client.post(
                reverse('frontend:add_slaves'), {
                    'name': data.name,
                    'ip_address': data.ip_address,
                    'mac_address': data.mac_address
                })

            self.assertEqual(api_response.status_code, 200)
            self.assertJSONEqual(
                api_response.content.decode('utf-8'),
                Status.ok("").to_json())

        #test if all slaves get displayed
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

        #add first slave
        api_response = self.client.post(
            reverse('frontend:add_slaves'), {
                'name': data.name,
                'ip_address': data.ip_address,
                'mac_address': data.mac_address
            })
        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(
            api_response.content.decode('utf-8'),
            Status.ok("").to_json())

        #insert data a second time
        api_response = self.client.post(
            reverse('frontend:add_slaves'), {
                'name': data.name,
                'ip_address': data.ip_address,
                'mac_address': data.mac_address
            })

        #test if the response contains a JSONobject with the error
        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(
            api_response.content.decode('utf-8'),
            json.loads(
                Status.err({
                    "name": ["Slave with this Name already exists."],
                    "ip_address":
                    ["Slave with this Ip address already exists."],
                    "mac_address":
                    ["Slave with this Mac address already exists."]
                }).to_json()))

        #test if the slave is still in the database
        self.assertTrue(
            SlaveModel.objects.filter(
                name=data.name,
                ip_address=data.ip_address,
                mac_address=data.mac_address).exists())

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
        #test if response was successfull
        self.assertEqual(api_response.status_code, 200)

        #see if message contains the error
        self.assertJSONEqual(
            api_response.content.decode('utf-8'),
            json.loads(
                Status.err({
                    "ip_address": ["Enter a valid IPv4 or IPv6 address."],
                    "mac_address": ["Enter a valid MAC Address."]
                }).to_json()))

        #test if the database does not contain the false slave
        self.assertFalse(
            SlaveModel.objects.filter(
                name=data.name,
                ip_address=data.ip_address,
                mac_address=data.mac_address).exists())

    def test_add_slave_no_post(self):
        data = SlaveModel(
            name="add_slave_5",
            ip_address="ip address",
            mac_address="mac address")

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

        #make a request for every slave in the data_set
        for data in data_set:
            api_response = self.client.post(
                reverse('frontend:add_slaves'), {
                    'name': data.name,
                    'ip_address': data.ip_address,
                    'mac_address': data.mac_address
                })

            self.assertEqual(api_response.status_code, 200)
            self.assertJSONEqual(
                api_response.content.decode('utf-8'),
                Status.ok("").to_json())

        #get all the database entries because the ids are needed to delete
        data_in_database_set = []
        for data in data_set:
            data_in_database_set.append(
                SlaveModel.objects.filter(
                    name=data.name,
                    ip_address=data.ip_address,
                    mac_address=data.mac_address).get())

        #make a request to delete the slave entry
        for data in data_in_database_set:
            api_response = self.client.delete('/api/slave/' + str(data.id))
            self.assertEqual(api_response.status_code, 200)
            self.assertJSONEqual(
                api_response.content.decode('utf-8'),
                Status.ok("").to_json())
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

        #make a request for every slave in the data_set
        for data in data_set_1:
            api_response = self.client.post(
                reverse('frontend:add_slaves'), {
                    'name': data.name,
                    'ip_address': data.ip_address,
                    'mac_address': data.mac_address
                })
            self.assertEqual(api_response.status_code, 200)
            self.assertJSONEqual(
                api_response.content.decode('utf-8'),
                Status.ok("").to_json())

        #get all the database entries because the ids are needed to delete
        data_in_database_set = []
        for data in data_set_1:
            data_in_database_set.append(
                SlaveModel.objects.filter(
                    name=data.name,
                    ip_address=data.ip_address,
                    mac_address=data.mac_address).get())

        #make an edit request for every entry in data_set_1 with the data from dataset 2
        for (data, new_data) in zip(data_in_database_set, data_set_2):
            api_response = self.client.put(
                '/api/slave/' + str(data.id),
                data=urlencode({
                    'name': new_data.name,
                    'ip_address': new_data.ip_address,
                    'mac_address': new_data.mac_address
                }))
            self.assertEqual(api_response.status_code, 200)
            self.assertJSONEqual(
                api_response.content.decode('utf-8'),
                Status(Status.ID_OK, "").to_json())

        #test if the changes have affected the database
        for (data, new_data) in zip(data_set_1, data_set_2):
            self.assertFalse(
                SlaveModel.objects.filter(
                    name=data.name,
                    ip_address=data.ip_address,
                    mac_address=data.mac_address).exists())
            self.assertTrue(
                SlaveModel.objects.filter(
                    name=new_data.name,
                    ip_address=new_data.ip_address,
                    mac_address=new_data.mac_address).exists())

    def test_edit_slave_already_exists(self):
        api_response = self.client.post(
            reverse('frontend:add_slaves'), {
                'name': 'edit_slave_fail_0',
                'ip_address': '0.0.4.0',
                'mac_address': '00:00:00:00:04:00'
            })
        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(
            api_response.content.decode('utf-8'),
            Status.ok("").to_json())

        api_response = self.client.post(
            reverse('frontend:add_slaves'), {
                'name': 'edit_slave_fail_1',
                'ip_address': '0.0.4.1',
                'mac_address': '00:00:00:00:04:01'
            })
        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(
            api_response.content.decode('utf-8'),
            Status.ok("").to_json())

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
        self.assertJSONEqual(
            api_response.content.decode('utf-8'),
            json.loads(
                Status.err({
                    "name": ["Slave with this Name already exists."],
                    "ip_address":
                    ["Slave with this Ip address already exists."],
                    "mac_address":
                    ["Slave with this Mac address already exists."]
                }).to_json()))

    def test_add_program(self):
        SlaveModel(
            name='add_program',
            ip_address='0.0.5.0',
            mac_address='00:00:00:00:04:00',
        ).save()
        model = SlaveModel.objects.get(name='add_program')

        #add all programs
        for id in range(100):
            api_response = self.client.post(
                '/api/programs', {
                    'name': 'name' + str(id),
                    'path': 'path' + str(id),
                    'arguments': 'arguments' + str(id),
                    'slave': str(model.id)
                })
            self.assertEqual(api_response.status_code, 200)
            self.assertJSONEqual(
                api_response.content.decode('utf-8'),
                Status(Status.ID_OK, "").to_json())

        #test if all programs are in the database
        for id in range(100):
            self.assertTrue(
                ProgramModel.objects.filter(
                    name='name' + str(id),
                    path='path' + str(id),
                    arguments='arguments' + str(id),
                    slave=model))

        #delete all entries
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
                'slave': str(model.id)
            })

        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(
            api_response.content.decode('utf-8'),
            json.loads(
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
                }).to_json()))

        #delete slave
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
                'slave': str(model.id)
            })

        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(
            api_response.content.decode('utf-8'),
            json.loads(Status.ok('').to_json()))

        #try to add program with the same name

        api_response = self.client.post(
            '/api/programs', {
                'name': 'name',
                'path': 'path',
                'arguments': '',
                'slave': str(model.id)
            })

        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(
            api_response.content.decode('utf-8'),
            json.loads(
                Status.err({
                    'name':
                    ['Program with this Name already exists on this Client.']
                }).to_json()))

        #delete slave
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

    # test wake on lan
    def test_wol(self):
        # add a test slave
        test_model = SlaveModel(
            name='wol_client',
            ip_address='0.0.5.0',
            mac_address='00:00:00:00:05:00')
        test_model.save()

        # non existent slave
        res = self.client.get(
            path=reverse('frontend:wol_slave', args=[999999]))
        self.assertEqual(res.status_code, 500)
        self.assertEqual(res.json()['status'], 'err')
        self.assertEqual(
            res.json()['payload'],
            "DoesNotExist('Slave matching query does not exist.',)",
        )

        # wrong http method
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

        #saving slave in database
        slave.save()

        # get the database entry for the slave because his id is needed to delete a program
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

        #saving programs in database
        for data in data_set:
            data.save()

        # get all the database entries because the ids are needed to delete
        data_in_database_set = []
        for data in data_set:
            data_in_database_set.append(
                ProgramModel.objects.get(name=data.name))

        # make a request to delete the program entry
        for data in data_in_database_set:
            api_response = self.client.delete('/api/program/' + str(data.id))
            self.assertEqual(api_response.status_code, 200)
            self.assertEquals(api_response.json()['status'], 'ok')
            self.assertFalse(ProgramModel.objects.filter(id=data.id).exists())

    def test_manage_program_wrong_http_method(self):
        api_response = self.client.get("/api/program/0")
        self.assertEqual(api_response.status_code, 403)

    def test_modify_program(self):
        #fill database
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
                slave=slave).save()
            programs.append(
                ProgramModel.objects.get(
                    name="name_" + str(i),
                    path="path_" + str(i),
                    arguments="arguments_" + str(i),
                    slave=slave))

        for i in range(100):
            api_response = self.client.put(
                "/api/program/" + str(programs[i].id),
                data=urlencode({
                    'name': str(i),
                    'path': str(i),
                    'arguments': str(i),
                    'slave': str(slave.id)
                }))

            self.assertEqual(api_response.status_code, 200)
            self.assertJSONEqual(
                api_response.content.decode('utf-8'),
                json.loads(Status.ok("").to_json()))

        #clear database
        slave.delete()

    def test_modify_program_fail(self):
        #fill database
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
                'slave': str(slave.id)
            }))

        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(
            api_response.content.decode('utf-8'),
            json.loads(
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
                }).to_json()))
        slave.delete()

    def test_edit_program_unique_fail(self):
        #fill database
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
            name="", path="path", arguments="", slave=slave)

        api_response = self.client.put(
            "/api/program/" + str(program.id),
            data=urlencode({
                'name': 'name',
                'path': 'path',
                'arguments': '',
                'slave': str(slave.id)
            }))

        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(
            api_response.content.decode('utf-8'),
            json.loads(
                Status.err({
                    "name":
                    ["Program with this Name already exists on this Client."]
                }).to_json()))

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
            name="program", path="path", arguments="", slave=slave)

        SlaveStatusModel(slave=slave, boottime=timezone.now()).save()

        # connect client
        client = WSClient()
        client.join_group("client_" + str(slave.id))

        # connect webinterface to /notifications
        webinterface = WSClient()
        webinterface.join_group('notifications')

        api_response = self.client.post("/api/program/" + str(program.id))
        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(
            api_response.content.decode('utf-8'),
            json.loads(Status.ok("").to_json()),
        )

        # test if the client receives the command
        self.assertJSONEqual(
            Command(
                method='execute',
                pid=program.id,
                path=program.path,
                arguments=split(program.arguments),
            ).to_json(), client.receive())

        #test if the webinterface gets the "started" message
        self.assertJSONEqual(
            Status.ok({
                'program_status': 'started',
                'pid': program.id
            }).to_json(), webinterface.receive())

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
            name="program", path="path", arguments="", slave=slave)

        client = WSClient()
        client.join_group("commands_" + str(slave.id))

        api_response = self.client.post("/api/program/" + str(program.id))
        self.assertEqual(api_response.status_code, 200)

        self.assertJSONEqual(
            api_response.content.decode('utf-8'),
            json.loads(
                Status.err('Can not start {} because {} is offline!'.format(
                    program.name, slave.name)).to_json()))

        ws_response = client.receive()
        self.assertEqual(None, ws_response)
        slave.delete()

    def test_shutdown_slave(self):
        SlaveModel(
            name='test_shutdown_slave',
            ip_address='0.0.9.0',
            mac_address='00:00:00:00:09:00',
        ).save()
        slave = SlaveModel.objects.get(name='test_shutdown_slave')

        SlaveStatusModel(boottime=timezone.now(), slave=slave).save()

        # connect slave to websocket
        ws_client = WSClient()
        ws_client.join_group('client_' + str(slave.id))

        # make request
        api_response = self.client.get(
            path=reverse('frontend:shutdown_slave', args=[slave.id]))
        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(
            Status.ok('').to_json(), api_response.content.decode('utf-8'))

        # test if the slave gets the shutdown request
        self.assertJSONEqual(
            Command(method='shutdown').to_json(), ws_client.receive())

        slave.delete()

    def test_shutdown_slave_unknown_slave(self):
        # make request
        api_response = self.client.get('/api/slave/111/shutdown')
        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(
            Status.err('Can not shutdown unknown Client').to_json(),
            api_response.content.decode('utf-8'))

    def test_shutdown_slave_offline_slave(self):
        SlaveModel(
            name='test_shutdown_slave_offline_slave',
            ip_address='0.0.9.1',
            mac_address='00:00:00:00:09:01',
        ).save()
        slave = SlaveModel.objects.get(
            name='test_shutdown_slave_offline_slave')

        # make request
        api_response = self.client.get(
            reverse('frontend:shutdown_slave', args=[slave.id]))
        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(
            Status.err('Can not shutdown offline Client').to_json(),
            api_response.content.decode('utf-8'))

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

        #add all programs
        for id in range(100):
            api_response = self.client.post(
                '/api/files', {
                    'name': 'name' + str(id),
                    'sourcePath': 'sourcePath' + str(id),
                    'destinationPath': 'destinationPath' + str(id),
                    'slave': str(model.id)
                })
            self.assertEqual(api_response.status_code, 200)
            self.assertJSONEqual(
                api_response.content.decode('utf-8'),
                Status(Status.ID_OK, "").to_json())

        #test if all programs are in the database
        for id in range(100):
            self.assertTrue(
                FileModel.objects.filter(
                    name='name' + str(id),
                    sourcePath='sourcePath' + str(id),
                    destinationPath='destinationPath' + str(id),
                    slave=model))

        #delete all entries
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

        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(
            api_response.content.decode('utf-8'),
            json.loads(
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
                }).to_json()))

        #delete slave
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
                'slave': str(model.id)
            })

        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(
            api_response.content.decode('utf-8'),
            json.loads(Status.ok('').to_json()))

        #try to add program with the same name

        api_response = self.client.post(
            '/api/files', {
                'name': 'name',
                'sourcePath': 'sourcePath',
                'destinationPath': 'destinationPath',
                'slave': str(model.id)
            })

        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(
            api_response.content.decode('utf-8'),
            json.loads(
                Status.err({
                    'name':
                    ['File with this Name already exists on this Client.']
                }).to_json()))

        #delete slave
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

        self.assertJSONEqual(
            json.dumps(ws_client.receive()),
            Command(method="boottime", sid=slave.id).to_json())

        # test if the client is now part of the right groups
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

        #connect client on /commands
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.connect',
            path='/commands',
            content={'client': ['0.0.10.1', '00:00:00:00:10:01']},
        )

        #connect webinterface on /notifications
        webinterface = WSClient()
        webinterface.send_and_consume(
            'websocket.connect',
            path='/notifications',
        )

        #test for boottime request on client
        self.assertJSONEqual(
            json.dumps(ws_client.receive()),
            Command(method="boottime", sid=slave.id).to_json())

        SlaveStatusModel(slave=slave, boottime=timezone.now()).save()

        ws_client.send_and_consume('websocket.disconnect', path='/commands')

        # test if SlaveStatus was removed
        self.assertFalse(SlaveStatusModel.objects.filter(slave=slave).exists())

        # test if the client was removed from the correct groups
        Group('clients').send({'text': 'ok'}, immediately=True)
        self.assertIsNone(ws_client.receive())

        Group('client_{}'.format(slave.id)).send(
            {
                'text': 'ok'
            },
            immediately=True,
        )
        self.assertIsNone(ws_client.receive())

        # test if a "disconnected" message has been send to the webinterface
        self.assertJSONEqual(
            Status.ok({
                'slave_status': 'disconnected',
                'sid': str(slave.id)
            }).to_json(), webinterface.receive())

        slave.delete()

    def test_ws_notifications_connect_and_ws_disconnect(self):
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.connect',
            path='/notifications',
        )
        ws_client.send_and_consume(
            'websocket.disconnect',
            path='/notifications',
        )

    def test_ws_notifications_receive_fail(self):
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/notifications',
        )
        self.assertIsNone(ws_client.receive())

    def test_ws_notifications_receive_boottime(self):
        SlaveModel(
            name="test_ws_notifications_receive_boottime",
            ip_address='0.0.10.2',
            mac_address='00:00:00:00:10:02').save()
        slave = SlaveModel.objects.get(
            name="test_ws_notifications_receive_boottime",
            ip_address='0.0.10.2',
            mac_address='00:00:00:00:10:02')

        #connect webinterface on /notifications
        webinterface = WSClient()
        webinterface.send_and_consume(
            'websocket.connect', path='/notifications')

        #send bootime answer
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/notifications',
            content={
                'text':
                Status.ok({
                    'method':
                    'boottime',
                    'boottime':
                    datetime.strftime(timezone.now(), '%Y-%m-%d %H:%M:%S'),
                    'sid':
                    slave.id
                }).to_json()
            })
        self.assertTrue(SlaveStatusModel.objects.filter(slave=slave).exists())

        #test if a connected message was send on /notifications
        self.assertJSONEqual(
            Status.ok({
                'slave_status': 'connected',
                'sid': str(slave.id)
            }).to_json(), webinterface.receive())

        slave.delete()

    def test_ws_notifications_receive_execute(self):
        SlaveModel(
            name="test_ws_notifications_receive_execute",
            ip_address='0.0.10.3',
            mac_address='00:00:00:00:10:03').save()
        slave = SlaveModel.objects.get(
            name="test_ws_notifications_receive_execute",
            ip_address='0.0.10.3',
            mac_address='00:00:00:00:10:03')

        ProgramModel(
            name='program', path='path', arguments='', slave=slave).save()

        program = ProgramModel.objects.get(
            name='program', path='path', arguments='', slave=slave)

        ProgramStatusModel(program=program, started=timezone.now()).save()

        # connect webinterface
        webinterface = WSClient()
        webinterface.send_and_consume(
            'websocket.connect',
            path='/notifications',
        )

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/notifications',
            content={
                'text':
                Status.ok({
                    'method': 'execute',
                    'code': str(0),
                    'pid': str(program.id)
                }).to_json()
            })

        query = ProgramStatusModel.objects.filter(program=program, code=0)
        self.assertTrue(query.count() == 1)
        self.assertIsNotNone(query.first().stopped)

        # test if the webinterface gets the "finished" message
        self.assertJSONEqual(
            Status.ok({
                'program_status': 'finished',
                'pid': str(program.id),
                'code': str(0)
            }).to_json(), webinterface.receive())

        slave.delete()

    def test_ws_notifications_receive_status_err(self):
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/notifications',
            content={'text': Status.err("").to_json()},
        )
        self.assertIsNone(ws_client.receive())

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
    def test_slave_insert_valid(self):
        mod = SlaveModel(
            name="Tommo3",
            ip_address="192.168.5.39",
            mac_address="00:02:00:00:00:00",
        )
        mod.full_clean()
        mod.save()
        self.assertTrue(SlaveModel.objects.filter(name="Tommo3").exists())

    def flush_error(self):
        from .urls import flush
        flush('testssss')

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
            name="test", path="None", arguments="None", slave=slave)
        prog.save()

        status_slave = SlaveStatusModel(slave=slave, boottime=datetime.now())
        status_slave.save()

        status_program = ProgramStatusModel(prog.id, "None", datetime.now())
        status_program.save()

        self.assertEqual(SlaveStatusModel.objects.count(), 1)
        self.assertEqual(ProgramStatusModel.objects.count(), 1)

        from .urls import flush
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
        string = '{"name": "test", "files": [{"index": 0, "slave": 0, "file": "no name"}],"programs": [{"index": 0, "slave": 0, "program": "no name"}]}'

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

        a = ScriptEntryProgram(0, program.id, slave.id).as_model(script)
        b = ScriptEntryProgram(0, program.name, slave.name).as_model(script)
        a.save()
        self.assertRaises(IntegrityError, b.save)

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

        self.assertRaises(ValueError, ScriptEntryProgram.from_query, Dummy(),
                          "not int", "not str")
        self.assertRaises(ValueError, ScriptEntryProgram.from_query, Dummy(),
                          "int", "not str")

        self.assertRaises(ValueError, ScriptEntryFile.from_query, Dummy(),
                          "not int", "not str")
        self.assertRaises(ValueError, ScriptEntryFile.from_query, Dummy(),
                          "int", "not str")
