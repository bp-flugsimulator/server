from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from urllib.parse import urlencode
from utils import Status

import json

from .models import Slave as SlaveModel
from .models import Program as ProgramModel
from .models import validate_mac_address

def fill_database_slaves_set_1():
    data_set = [
        SlaveModel(
            name="Tommo1",
            ip_address="192.168.2.39",
            mac_address="00:00:00:00:00:00"),
        SlaveModel(
            name="Tommo2",
            ip_address="192.168.3.39",
            mac_address="02:00:00:00:00:00"),
        SlaveModel(
            name="Tommo3",
            ip_address="192.168.5.39",
            mac_address="00:02:00:00:00:00"),
        SlaveModel(
            name="Tommo4",
            ip_address="192.168.6.39",
            mac_address="00:00:02:00:00:00"),
        SlaveModel(
            name="Tommo5",
            ip_address="192.168.7.39",
            mac_address="00:00:00:02:00:00")
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
                mac_address="00:00:00:00:01:00"),
            SlaveModel(
                name="add_slave_1",
                ip_address="0.0.1.1",
                mac_address="00:00:00:00:01:01"),
            SlaveModel(
                name="add_slave_2",
                ip_address="0.0.1.2",
                mac_address="00:00:00:00:01:02"),
            SlaveModel(
                name="add_slave_3",
                ip_address="0.0.1.3",
                mac_address="00:00:00:00:01:03"),

        ]

        #make a request for every slave in the data_set
        for data in data_set:
            api_response = self.client.post(reverse('frontend:add_slaves'),{'name': data.name, 'ip_address': data.ip_address, 'mac_address':data.mac_address})

            self.assertEqual(api_response.status_code, 200)
            self.assertJSONEqual(api_response.content.decode('utf-8'), Status.ok("").to_json())

        #test if all slaves get displayed
        view_response =  self.client.get(reverse('frontend:slaves'))
        for data in data_set:
            self.assertContains(view_response, data.name)
            self.assertContains(view_response, data.ip_address)
            self.assertContains(view_response, data.mac_address)


    def test_add_slave_double_entry_fail(self):
        data = SlaveModel(name="add_slave_4", ip_address="0.0.1.4",mac_address="00:00:00:00:01:04")


        #add first slave
        api_response = self.client.post(reverse('frontend:add_slaves'),{'name': data.name, 'ip_address': data.ip_address, 'mac_address':data.mac_address})
        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(api_response.content.decode('utf-8'), Status.ok("").to_json())

        #insert data a second time
        api_response = self.client.post(reverse('frontend:add_slaves'),{'name': data.name, 'ip_address': data.ip_address, 'mac_address':data.mac_address})

        #test if the response contains a JSONobject with the error
        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(api_response.content.decode('utf-8'),Status.err('{"name": ["Slave with this Name already exists."], "ip_address": ["Slave with this Ip address already exists."], "mac_address": ["Slave with this Mac address already exists."]}').to_json())

        #test if the slave is still in the database
        self.assertTrue(SlaveModel.objects.filter(name=data.name,ip_address=data.ip_address,mac_address=data.mac_address).exists())

    def test_add_slave_false_input_fail(self):
        data = SlaveModel(name="add_slave_5", ip_address="ip address",mac_address="mac address")

        api_response = self.client.post(reverse('frontend:add_slaves'),{'name':data.name , 'ip_address': data.ip_address, 'mac_address':data.mac_address})
        #test if response was successfull
        self.assertEqual(api_response.status_code, 200)

        #see if message contains the error
        self.assertJSONEqual(api_response.content.decode('utf-8'), Status.err('{"ip_address": ["Enter a valid IPv4 or IPv6 address."], "mac_address": ["Enter a valid MAC Address."]}').to_json())

        #test if the database does not contain the false slave
        self.assertFalse(SlaveModel.objects.filter(name=data.name,ip_address=data.ip_address,mac_address=data.mac_address).exists())

    def test_add_slave_no_post(self):
        data = SlaveModel(name="add_slave_5", ip_address="ip address",mac_address="mac address")

        api_response = self.client.get(reverse('frontend:add_slaves'))
        self.assertEqual(api_response.status_code,403)

    def test_manage_slave_forbidden(self):
        api_response = self.client.get("/api/slave/0")
        self.assertEqual(api_response.status_code,403)


    def test_remove_slave(self):
        data_set = [
            SlaveModel(
                name="remove_slave_0",
                ip_address="0.0.2.0",
                mac_address="00:00:00:00:02:00"),
            SlaveModel(
                name="remove_slave_1",
                ip_address="0.0.2.1",
                mac_address="00:00:00:00:02:01"),
            SlaveModel(
                name="remove_slave_2",
                ip_address="0.0.2.2",
                mac_address="00:00:00:00:02:02"),
            SlaveModel(
                name="remove_slave_3",
                ip_address="0.0.2.3",
                mac_address="00:00:00:00:02:03"),

        ]

        #make a request for every slave in the data_set
        for data in data_set:
            api_response = self.client.post(reverse('frontend:add_slaves'),{'name': data.name, 'ip_address': data.ip_address, 'mac_address':data.mac_address})

            self.assertEqual(api_response.status_code, 200)
            self.assertJSONEqual(api_response.content.decode('utf-8'), Status.ok("").to_json())

        #get all the database entries because the ids are needed to delete
        data_in_database_set = []
        for data in data_set:
            data_in_database_set.append(SlaveModel.objects.filter(name=data.name, ip_address=data.ip_address, mac_address=data.mac_address).get())

        #make a request to delete the slave entry
        for data in data_in_database_set:
            api_response = self.client.delete('/api/slave/'+ str(data.id))
            self.assertEqual(api_response.status_code, 200)
            self.assertJSONEqual(api_response.content.decode('utf-8'), Status.ok("").to_json())
            self.assertFalse(SlaveModel.objects.filter(id=data.id).exists())

    def test_edit_slave(self):
        data_set_1 = [
            SlaveModel(
                name="edit_slave_0",
                ip_address="0.0.3.0",
                mac_address="00:00:00:00:03:00"),
            SlaveModel(
                name="edit_slave_1",
                ip_address="0.0.3.1",
                mac_address="00:00:00:00:03:01"),
            SlaveModel(
                name="edit_slave_2",
                ip_address="0.0.3.2",
                mac_address="00:00:00:00:03:02"),
            SlaveModel(
                name="edit_slave_3",
                ip_address="0.0.3.3",
                mac_address="00:00:00:00:03:03"),

        ]
        data_set_2 = [
            SlaveModel(
                name="edit_slave_4",
                ip_address="0.0.3.4",
                mac_address="00:00:00:00:03:04"),
            SlaveModel(
                name="edit_slave_5",
                ip_address="0.0.3.5",
                mac_address="00:00:00:00:03:05"),
            SlaveModel(
                name="edit_slave_6",
                ip_address="0.0.3.6",
                mac_address="00:00:00:00:03:06"),
            SlaveModel(
                name="edit_slave_7",
                ip_address="0.0.3.7",
                mac_address="00:00:00:00:03:07"),
        ]

        #make a request for every slave in the data_set
        for data in data_set_1:
            api_response = self.client.post(reverse('frontend:add_slaves'),{'name': data.name, 'ip_address': data.ip_address, 'mac_address':data.mac_address})
            self.assertEqual(api_response.status_code, 200)
            self.assertJSONEqual(api_response.content.decode('utf-8'), Status.ok("").to_json())

        #get all the database entries because the ids are needed to delete
        data_in_database_set = []
        for data in data_set_1:
            data_in_database_set.append(SlaveModel.objects.filter(name=data.name, ip_address=data.ip_address, mac_address=data.mac_address).get())

        #make an edit request for every entry in data_set_1 with the data from dataset 2
        for (data,new_data) in zip(data_in_database_set,data_set_2):
            api_response = self.client.put('/api/slave/' + str(data.id),data=urlencode({'name': new_data.name, 'ip_address':new_data.ip_address, 'mac_address':new_data.mac_address}))
            self.assertEqual(api_response.status_code, 200)
            self.assertJSONEqual(api_response.content.decode('utf-8'), Status(Status.ID_OK, "").to_json())

        #test if the changes have affected the database
        for (data, new_data) in zip(data_set_1, data_set_2):
            self.assertFalse(SlaveModel.objects.filter(name=data.name,ip_address=data.ip_address,mac_address=data.mac_address).exists())
            self.assertTrue(SlaveModel.objects.filter(name=new_data.name,ip_address=new_data.ip_address,mac_address=new_data.mac_address).exists())

    def test_edit_slave_already_exists(self):
        api_response = self.client.post(reverse('frontend:add_slaves'),{'name': 'edit_slave_fail_0', 'ip_address': '0.0.4.0', 'mac_address':'00:00:00:00:04:00'})
        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(api_response.content.decode('utf-8'), Status.ok("").to_json())

        api_response = self.client.post(reverse('frontend:add_slaves'),{'name': 'edit_slave_fail_1', 'ip_address': '0.0.4.1', 'mac_address':'00:00:00:00:04:01'})
        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(api_response.content.decode('utf-8'), Status.ok("").to_json())

        data = SlaveModel.objects.filter(name='edit_slave_fail_0',ip_address='0.0.4.0',mac_address='00:00:00:00:04:00').get()
        api_response = self.client.put("/api/slave/"+str(data.id),data=urlencode({'name': 'edit_slave_fail_1', 'ip_address': '0.0.4.1', 'mac_address':'00:00:00:00:04:01'}))
        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(api_response.content.decode('utf-8'), Status(Status.ID_ERR, '{"name": ["Slave with this Name already exists."], "ip_address": ["Slave with this Ip address already exists."], "mac_address": ["Slave with this Mac address already exists."]}').to_json())

    def test_add_program(self):
        SlaveModel(name='add_program',ip_address='0.0.5.0',mac_address='00:00:00:00:04:00').save()
        model = SlaveModel.objects.get(name='add_program')

        #add all programs
        for id in range(100):
            api_response = self.client.post('/api/programs',{'name':'name'+str(id),'path':'path'+str(id), 'arguments': 'arguments'+str(id), 'slave_id':str(model.id)})
            self.assertEqual(api_response.status_code, 200)
            self.assertJSONEqual(api_response.content.decode('utf-8'), Status(Status.ID_OK, "").to_json())

        #test if all programs are in the database
        for id in range(100):
            self.assertTrue(ProgramModel.objects.filter(name= 'name' + str(id),path= 'path' + str(id), arguments= 'arguments' + str(id),slave=model))

        #delete all entries
        model.delete()

    def test_add_program_fail(self):
        SlaveModel(name='add_program_fail',ip_address='0.0.6.0',mac_address='00:00:00:00:06:00').save()
        model = SlaveModel.objects.get(name='add_program_fail')

        long_str = ''

        for _ in range(2000):
            long_str += 'a'

        api_response = self.client.post('/api/programs',{'name':long_str, 'path': long_str, 'arguments': long_str, 'slave_id': str(model.id)})
        self.assertEqual(api_response.status_code, 200)
        print()
        self.assertJSONEqual(api_response.content.decode('utf-8'), Status(Status.ID_ERR, '{"name": ["Ensure this value has at most 200 characters (it has 2000)."], "path": ["Ensure this value has at most 200 characters (it has 2000)."], "arguments": ["Ensure this value has at most 200 characters (it has 2000)."]}').to_json())

        #delete slave
        model.delete()

    def test_add_program_unsupported_function(self):
        SlaveModel(name='add_program_unsupported',ip_address='0.0.7.0',mac_address='00:00:00:00:07:00').save()
        model = SlaveModel.objects.get(name='add_program_unsupported')

        api_response = self.client.delete('/api/programs')
        self.assertEqual(api_response.status_code, 403)
        SlaveModel.objects.get(name='add_program_unsupported',ip_address='0.0.7.0',mac_address='00:00:00:00:07:00').delete()

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
        self.assertEqual(res.json()['payload'], "DoesNotExist('Slave matching query does not exist.',)")

        # wrong http method
        res = self.client.post(
            path=reverse('frontend:wol_slave', args=[test_model.id]))
        self.assertEqual(res.status_code, 403)

        res = self.client.get(
            path=reverse('frontend:wol_slave', args=[test_model.id]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['status'], 'ok')


class DatabaseTests(TestCase):
    def test_slave_insert_valid(self):
        mod = SlaveModel(
            name="Tommo3",
            ip_address="192.168.5.39",
            mac_address="00:02:00:00:00:00")
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
        self.assertRaises(ValidationError, validate_mac_address, "00:02:23")

    def test_mac_validator_too_long(self):
        self.assertRaises(ValidationError, validate_mac_address,
                          "00:02:23:23:23:23:32")

    def test_mac_validator_too_long_inner(self):
        self.assertRaises(ValidationError, validate_mac_address,
                          "00:02:23:223:23:23")

    def test_mac_validator_too_short_inner(self):
        self.assertRaises(ValidationError, validate_mac_address,
                          "00:02:23:2:23:23")
