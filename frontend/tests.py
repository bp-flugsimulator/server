from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden

from .models import Slave as SlaveModel, validate_mac_address

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
        c = Client()
        response = c.get(reverse('frontend:welcome'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "welcome")

    def test_slave_get(self):
        data_set = fill_database_slaves_set_1()

        c = Client()
        response = c.get(reverse('frontend:slaves'))
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
        c = Client()

        #make a request for every slave in the data_set
        for data in data_set:
            api_response = c.post(reverse('frontend:add_slaves'),{'name': data.name, 'ip_address': data.ip_address, 'mac_address':data.mac_address})

            self.assertEqual(api_response.status_code, 200)
            self.assertJSONEqual(api_response.content.decode('utf-8'), "{}")

        #test if all slaves get displayed
        view_response =  c.get(reverse('frontend:slaves'))
        for data in data_set:
            self.assertContains(view_response, data.name)
            self.assertContains(view_response, data.ip_address)
            self.assertContains(view_response, data.mac_address)


    def test_add_slave_double_entry_fail(self):
        data = SlaveModel(name="add_slave_4", ip_address="0.0.1.4",mac_address="00:00:00:00:01:04")

        c = Client()

        #add first slave
        api_response = c.post(reverse('frontend:add_slaves'),{'name': data.name, 'ip_address': data.ip_address, 'mac_address':data.mac_address})
        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(api_response.content.decode('utf-8'), "{}")

        #insert data a second time
        api_response = c.post(reverse('frontend:add_slaves'),{'name': data.name, 'ip_address': data.ip_address, 'mac_address':data.mac_address})

        #test if the response contains a JSONobject with the error
        self.assertEqual(api_response.status_code, 200)
        self.assertJSONEqual(api_response.content.decode('utf-8'),'{"name":["Slave with this Name already exists."],"ip_address":["Slave with this Ip address already exists."],"mac_address":["Slave with this Mac address already exists."]}')

        #test if the slave is still in the database
        self.assertTrue(SlaveModel.objects.filter(name=data.name,ip_address=data.ip_address,mac_address=data.mac_address).exists())

    def test_add_slave_false_input_fail(self):
        data = SlaveModel(name="add_slave_5", ip_address="ip address",mac_address="mac address")

        c = Client()
        api_response = c.post(reverse('frontend:add_slaves'),{'name':data.name , 'ip_address': data.ip_address, 'mac_address':data.mac_address})
        #test if response was successfull
        self.assertEqual(api_response.status_code, 200)

        #see if message contains the error
        self.assertJSONEqual(api_response.content.decode('utf-8'), '{"ip_address":["Enter a valid IPv4 or IPv6 address."],"mac_address": ["Invalid MAC Address (too few parts): mac_addr"]}')

        #test if the database does not contain the false slave
        self.assertFalse(SlaveModel.objects.filter(name=data.name,ip_address=data.ip_address,mac_address=data.mac_address).exists())

    def test_add_slave_no_post(self):
        data = SlaveModel(name="add_slave_5", ip_address="ip address",mac_address="mac address")

        c = Client()
        api_response = c.get(reverse('frontend:add_slaves'))
        self.assertEqual(api_response.status_code,403)

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
