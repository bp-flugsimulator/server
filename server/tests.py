from django.test import TestCase

from .utils import StatusResponse
from utils.status import Status
from server.management.commands.compilesass import Command

import json
from os import remove
from os.path import isfile, isdir
from unittest import skipUnless

class StatusResponseTest(TestCase):
    def test_status_init(self):
        response = StatusResponse(Status.ok(''))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content.decode('utf-8')
                             , json.loads(Status.ok('').to_json()))

    def test_status_init_fail(self):
        self.assertRaisesMessage(TypeError,'Only Status objects are allowed here',
                                 StatusResponse.__init__,'data','args')


@skipUnless(isdir('node_modules'), 'There is no nodes folder')
class ManagementTest(TestCase):
    CSS_PATH = 'base/static/base/css/custom.css'
    def test_css_generation(self):
        # if there is already a custom.css file remove it
        if isfile(self.CSS_PATH):
            remove(self.CSS_PATH)
        com = Command()
        com.handle()
        self.assertTrue(isfile(self.CSS_PATH))


