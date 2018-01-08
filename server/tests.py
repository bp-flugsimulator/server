from django.test import TestCase

from .utils import StatusResponse
from utils.status import Status
from sass import CompileError
from server.management.commands.compilesass import Command as SassCommand
from server.management.commands.clean_npm import Command as CleanNpmCommand

import json
from os import remove, replace, mkdir, rmdir
from os.path import isfile, isdir


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
    NPM_PATH = 'node_modules'
    BACKUP_PATH = 'node_modules_backup'

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
        mkdir(self.NPM_PATH + '/test1')
        with open(self.NPM_PATH + '/test1/' + 'testfile.txt', 'a') as f:
            f.close()

        mkdir(self.NPM_PATH + '/test1/testdir')
        with open(self.NPM_PATH + '/test1/testdir/' + 'testfile.txt', 'a') as f:
            f.close()

        mkdir(self.NPM_PATH + '/test2')
        with open(self.NPM_PATH + '/test2/' + 'testfile.txt', 'a') as f:
            f.close()

        # create test dependency
        with open('test.html', 'w') as f:
            f.write("{% static 'node/test1/testdir/testfile.txt' %}")
            f.close()

        # execute command
        exception = None
        try:
            com = CleanNpmCommand()
            com.handle()

            self.assertTrue(isdir(self.NPM_PATH + '/test1/'))
            self.assertTrue(isdir(self.NPM_PATH + '/test1/testdir'))
            self.assertTrue(isfile(self.NPM_PATH + '/test1/testfile.txt'))
            self.assertTrue(isfile(self.NPM_PATH + '/test1/testdir/testfile.txt'))

            self.assertFalse(isdir(self.NPM_PATH + '/test2'))
        except Exception as err:
            exception = err
            try:
                remove(self.NPM_PATH + '/test2/' + 'testfile.txt')
            except:
                pass
            try:
                rmdir(self.NPM_PATH + '/test2')
            except:
                pass
        finally:
            # delete testfiles
            remove('test.html')
            remove(self.NPM_PATH + '/test1/testdir/' + 'testfile.txt')
            remove(self.NPM_PATH + '/test1/' + 'testfile.txt')
            rmdir(self.NPM_PATH + '/test1/testdir')
            rmdir(self.NPM_PATH + '/test1')
            rmdir(self.NPM_PATH)

            # restore backup
            if isdir(self.BACKUP_PATH):
                replace(src=self.BACKUP_PATH, dst=self.NPM_PATH)

        self.assertIsNone(exception)
