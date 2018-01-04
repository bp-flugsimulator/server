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

from .models import Slave as SlaveModel, validate_mac_address, Program as ProgramModel, SlaveStatus as SlaveStatusModel, ProgramStatus as ProgramStatusModel
from .consumers import ws_rpc_connect


def fill_database_slaves_set_1():
    data_set = [
        SlaveModel(
            name="Tommo1",
            ip_address="192.168.2.39",
            mac_address="00:00:00:00:00:00",
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


class ApiTests(TestCase):
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

        api_response = self.client.get(reverse('frontend:add_slaves'))
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

        client = WSClient()
        client.join_group("client_" + str(slave.id))

        api_response = self.client.post("/api/program/" + str(program.id))
        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(
            api_response.content.decode('utf-8'),
            json.loads(Status.ok("").to_json()),
        )

        ws_response = client.receive()
        self.assertJSONEqual(
            Command(
                method='execute',
                pid=program.id,
                path=program.path,
                arguments=split(program.arguments),
            ).to_json(), ws_response)
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

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.connect',
            path='/commands',
            content={'client': ['0.0.10.1', '00:00:00:00:10:01']},
        )

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
