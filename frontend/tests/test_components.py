"""
TESTCASE NAMING SCHEME

def test_<TEMPLATE TAG NAME>:
    pass

<TEMPLATE TAG NAME>:
    The name which is the same as the template tag.
"""

#  pylint: disable=C0111
#  pylint: disable=C0103

from django.test import TestCase


class ComponentTests(TestCase):  # pylint: disable=unused-variable
    def test_script_entry(self):
        from frontend.templatetags.components import script_entry
        response = script_entry("test")
        self.assertEqual({"script": "test"}, response)
