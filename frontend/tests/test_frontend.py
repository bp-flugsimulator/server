#  pylint: disable=C0111,C0103

from django.test import TestCase
from django.urls import reverse

from .factory import (
    SlaveFactory,
    ScriptFactory,
    ProgramFactory,
    FileFactory,
)


class FrontendTests(TestCase):
    def test_welcome_get(self):
        response = self.client.get(reverse('frontend:welcome'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "welcome")

    def test_slave_get_empty(self):
        slave = SlaveFactory()
        response = self.client.get(reverse('frontend:slaves'))
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, slave.name)
        self.assertContains(response, slave.mac_address)
        self.assertContains(response, slave.ip_address)

    def test_scripts_get(self):
        script = ScriptFactory()
        response = self.client.get(reverse('frontend:scripts'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Scripts")
        self.assertContains(response, script.name)

    def test_run_script_get(self):
        response = self.client.get(reverse('frontend:scripts_run'))
        self.assertEqual(response.status_code, 200)

    def test_slave_get(self):
        slave = SlaveFactory()
        program = ProgramFactory(slave=slave)
        file = FileFactory(slave=slave)

        response = self.client.get(reverse('frontend:slaves'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, slave.name)
        self.assertContains(response, program.name)
        self.assertContains(response, file.name)
