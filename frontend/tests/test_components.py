#  pylint: disable=C0111
#  pylint: disable=C0103

from django.test import TestCase

class ComponentTests(TestCase): # pylint: diasble=unused-variable
    def test_script_entry(self):
        from frontend.templatetags.components import script_entry
        response = script_entry("test")
        self.assertEqual({"script": "test"}, response)
        