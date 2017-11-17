from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.forms import ModelForm

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
