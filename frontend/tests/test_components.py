"""
TESTCASE NAMING SCHEME

def test_<TEMPLATE TAG NAME>:
    pass

<TEMPLATE TAG NAME>:
    The name which is the same as the template tag.
"""
# pylint: disable=missing-docstring,too-many-public-methods

from django.test import TestCase


class ComponentTests(TestCase):
    def test_script_entry(self):
        from frontend.templatetags.components import script_entry
        response = script_entry("test")
        self.assertEqual({"script": "test"}, response)
