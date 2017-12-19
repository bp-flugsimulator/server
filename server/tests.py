from django.test import TestCase

from .utils import StatusResponse
from utils.status import Status

import json

class StatusResponseTest(TestCase):
    def test_status_init(self):
        response = StatusResponse(Status.ok(''))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content.decode('utf-8')
                             , json.loads(Status.ok('').to_json()))

    def test_status_init_fail(self):
        self.assertRaisesMessage(TypeError,'Only Status objects are allowed here',
                                 StatusResponse.__init__,'data','args')
