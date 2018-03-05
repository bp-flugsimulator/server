"""
Move into Frontenend tests.
"""
#  pylint: disable=C0111,C0103

from os import getcwd, remove, mkdir, rmdir
from os.path import join, isdir

from django.test import TestCase
from django.urls import reverse


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
