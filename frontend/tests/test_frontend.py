"""
TESTCASE NAMING SCHEME

def test_<VIEW>_<OPTION>(self):
    pass

<VIEW>:
    Name of the view
<OPTION>:
    Optional suffix for more information

"""
# pylint: disable=missing-docstring,too-many-public-methods

from os import getcwd, remove, mkdir, rmdir
from os.path import join, isdir

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
        filesystem = FileFactory(slave=slave)

        response = self.client.get(reverse('frontend:slaves'))
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, slave.name)
        self.assertContains(response, program.name)
        self.assertContains(response, filesystem.name)


class DownloadTests(TestCase):
    DOWNLOAD_FOLDER = 'downloads'

    @classmethod
    def setUpClass(cls):
        if not isdir(cls.DOWNLOAD_FOLDER):
            mkdir(cls.DOWNLOAD_FOLDER)
        super().setUpClass()

    def test_download_page_no_folder(self):
        rmdir(self.DOWNLOAD_FOLDER)
        response = self.client.get(reverse('frontend:downloads'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'No files are present in the download folder',
            str(response.content),
        )

    def test_download_page_0_byte(self):
        with open(
                join(getcwd(), self.DOWNLOAD_FOLDER, 'testfile1.txt'),
                'w',
        ) as file:
            file.close()

        response = self.client.get(reverse('frontend:downloads'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            '0 B',
            str(response.content),
        )
        self.assertIn(
            'href="/static/downloads/testfile1.txt"',
            str(response.content),
        )

        remove(join(getcwd(), self.DOWNLOAD_FOLDER, 'testfile1.txt'), )

    def test_download_page_1_kib(self):
        with open(
                join(getcwd(), self.DOWNLOAD_FOLDER, 'testfile2.txt'),
                'w',
        ) as file:
            file.seek(pow(2, 10))
            file.write('\0')
            file.close()

        response = self.client.get(reverse('frontend:downloads'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            '1 KiB',
            str(response.content),
        )
        self.assertIn(
            'href="/static/downloads/testfile2.txt"',
            str(response.content),
        )

        remove(join(getcwd(), self.DOWNLOAD_FOLDER, 'testfile2.txt'), )

    def test_download_page_1_mib(self):
        with open(
                join(getcwd(), self.DOWNLOAD_FOLDER, 'testfile3.txt'),
                'w',
        ) as file:
            file.seek(pow(2, 20))
            file.write('\0')
            file.close()

        response = self.client.get(reverse('frontend:downloads'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            '1 MiB',
            str(response.content),
        )
        self.assertIn(
            'href="/static/downloads/testfile3.txt"',
            str(response.content),
        )

        remove(join(getcwd(), self.DOWNLOAD_FOLDER, 'testfile3.txt'), )

    def test_download_page_1_gib(self):
        with open(
                join(getcwd(), self.DOWNLOAD_FOLDER, 'testfile4.txt'),
                'w',
        ) as file:
            file.seek(pow(2, 30))
            file.write("\0")
            file.close()

        response = self.client.get(reverse('frontend:downloads'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            '1 GiB',
            str(response.content),
        )
        self.assertIn('href="/static/downloads/testfile4.txt"',
                      str(response.content))

        remove(join(getcwd(), self.DOWNLOAD_FOLDER, 'testfile4.txt'), )
