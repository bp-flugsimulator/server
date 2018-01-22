#  pylint: disable=C0111
#  pylint: disable=C0103

from django.test import TestCase
from django.urls import reverse

from frontend.models import (
    Slave as SlaveModel,
    Program as ProgramModel,
    File as FileModel,
    Script as ScriptModel,
)

from frontend.scripts import Script, ScriptEntryFile, ScriptEntryProgram
from frontend.tests.utils import fill_database_slaves_set_1


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
        
    def test_slave_with_program_get(self):
        slave = SlaveModel(
            name='slave',
            ip_address='127.0.0.1',
            mac_address='00:00:00:00:00:00')
        slave.save()
        ProgramModel(
            name='p_asdodahgh',
            path='path',
            arguments='',
            slave=slave,
        ).save()
        FileModel(
            name='f_asdodahgh',
            sourcePath='src',
            destinationPath='dst',
            slave=slave,
        ).save()

        response = self.client.get(reverse('frontend:slaves'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('p_asdodahgh', str(response.content))
        self.assertIn('f_asdodahgh', str(response.content))
