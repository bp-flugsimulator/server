from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError


from .models import Slave as SlaveModel

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

            #test if response is a redirect (code 302 = FOUND commonly used for redirect)
            self.assertEqual(api_response.status_code, 302)
            self.assertRedirects(api_response, reverse('frontend:slaves'))


        #test if all slaves are in the database
        for data in data_set:
            self.assertTrue(SlaveModel.objects.filter(name=data.name, ip_address=data.ip_address, mac_address=data.mac_address).exists())

        #test if all slaves get displayed
        view_response =  c.get(reverse('frontend:slaves'))
        for data in data_set:
            self.assertContains(view_response, data.name)
            self.assertContains(view_response, data.ip_address)
            self.assertContains(view_response, data.mac_address)

    def test_add_slave_double_entry_fail(self):
        data = SlaveModel(name="add_slave_4", ip_address="0.0.1.4",mac_address="00:00:00:00:01:04")

        c = Client()

        api_response = c.post(reverse('frontend:add_slaves'),{'name': data.name, 'ip_address': data.ip_address, 'mac_address':data.mac_address})
        #test if response is a redirect (code 302 = FOUND commonly used for redirect)
        self.assertEqual(api_response.status_code, 302)
        self.assertRedirects(api_response, reverse('frontend:slaves'))
        view_response = c.get(reverse('frontend:slaves'))

        #insert data a second time and follow the redirect
        view_response = c.post(reverse('frontend:add_slaves'),{'name': data.name, 'ip_address': data.ip_address, 'mac_address':data.mac_address}, follow=True)
        #test if response is a redirected
        self.assertEqual(view_response.status_code, 200)

        #see if message contains the error
        messages = list(view_response.context['messages'])
        self.assertTrue(messages)
        self.assertEqual('Slave with this Ip address already exists. Slave with this Mac address already exists. ', str(messages[0]))

    def test_add_slave_false_input_fail(self):
        data = SlaveModel(name="add_slave_5", ip_address="ip address",mac_address="mac address")

        c = Client()
        view_response = c.post(reverse('frontend:add_slaves'),{'name':data.name , 'ip_address': data.ip_address, 'mac_address':data.mac_address}, follow=True)
        #test if response is a redirected
        self.assertEqual(view_response.status_code, 200)

        #see if message contains the error
        messages = list(view_response.context['messages'])
        self.assertTrue(messages)
        self.assertTrue("is not a valid IP Address" in str(messages[0]))
        self.assertTrue("is not a valid MAC Address" in str(messages[0]))



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
