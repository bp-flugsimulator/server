# pylint: disable=C0111

import json
from os import remove, replace, mkdir, rmdir, getcwd
from os.path import isfile, isdir, join
from sass import CompileError
from django.test import TestCase
from utils.status import Status
from server.management.commands.compilesass import Command as SassCommand
from server.management.commands.clean_npm import Command as CleanNpmCommand

from .utils import StatusResponse


class StatusResponseTest(TestCase):
    def test_status_init(self):
        response = StatusResponse(Status.ok(''))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content.decode('utf-8'),
            json.loads(Status.ok('').to_json()))

    def test_status_init_fail(self):
        self.assertRaisesMessage(TypeError,
                                 'Only Status objects are allowed here',
                                 StatusResponse.__init__, 'data', 'args')


class ManagementTest(TestCase):
    CSS_PATH = 'base/static/base/css/custom.css'
    NPM_PATH = join(getcwd(), 'node_modules')
    BACKUP_PATH = join(getcwd(), 'node_modules_backup')

    def test_css_generation(self):
        # if there is already a custom.css file remove it
        if isfile(self.CSS_PATH):
            remove(self.CSS_PATH)
        com = SassCommand()
        if not isdir('node_modules'):
            with self.assertRaises(CompileError):
                com.handle()
        else:
            com.handle()
            self.assertTrue(isfile(self.CSS_PATH))

    def test_clean_npm(self):
        # if node_modules exists back it up
        if isdir(self.NPM_PATH):
            replace(src=self.NPM_PATH, dst=self.BACKUP_PATH)

        # create package directory
        mkdir(self.NPM_PATH)

        # create two packages
        mkdir(join(self.NPM_PATH, 'test1'))
        with open(join(self.NPM_PATH, 'test1', 'testfile.txt'), 'w') as file:
            file.close()

        mkdir(join(self.NPM_PATH, 'test1', 'testdir'))
        with open(
                join(self.NPM_PATH, 'test1', 'testdir', 'testfile.txt'),
                'w') as file:
            file.close()

        mkdir(join(self.NPM_PATH, 'test2'))
        with open(join(self.NPM_PATH, 'test2', 'testfile.txt'), 'w') as file:
            file.close()

        # create test dependency
        with open('test.html', 'w') as file:
            file.write("{% static 'node/test1/testdir/testfile.txt' %}")
            file.close()

        # execute command
        exception = None
        try:
            com = CleanNpmCommand()
            com.handle()

            self.assertTrue(isdir(join(self.NPM_PATH, 'test1')))
            self.assertTrue(isdir(join(self.NPM_PATH, 'test1', 'testdir')))
            self.assertTrue(
                isfile(join(self.NPM_PATH, 'test1', 'testfile.txt')))
            self.assertTrue(
                isfile(
                    join(self.NPM_PATH, 'test1', 'testdir', 'testfile.txt')))

            self.assertFalse(isdir(join(self.NPM_PATH, 'test2')))
        except Exception as err:  # pylint: disable=W0703
            exception = err
            try:
                remove(join(self.NPM_PATH, 'test2', 'testfile.txt'))
            except exception:  # pylint: disable=W0703
                print('could not delete node/test2/testfile.txt,because:\n' +
                      str(exception))
            try:
                rmdir(join(self.NPM_PATH, 'test2'))
            except exception:  # pylint: disable=W0703
                print('could not delete node/test2/ ,because:\n' +
                      str(exception))
        finally:
            # delete testfiles
            remove('test.html')
            remove(join(self.NPM_PATH, 'test1', 'testdir', 'testfile.txt'))
            remove(join(self.NPM_PATH, 'test1', 'testfile.txt'))
            rmdir(join(self.NPM_PATH, 'test1', 'testdir'))
            rmdir(join(self.NPM_PATH, 'test1'))
            rmdir(self.NPM_PATH)

            # restore backup
            if isdir(self.BACKUP_PATH):
                replace(src=self.BACKUP_PATH, dst=self.NPM_PATH)

        self.assertIsNone(exception)
