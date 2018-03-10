"""
TESTCASE NAMEING SCHEME

def test_<NAME>(self):
    pass

<NAME>:
    error name with `_base` suffix if it is a base error.
"""
# pylint: disable=missing-docstring,too-many-public-methods

from django.test import TestCase

from frontend.errors import (
    FilesystemError,
    ProgramError,
    QueryError,
    ScriptError,
)


class BaseErrorTests(TestCase):
    def test_filesystem_base(self):
        error = FilesystemError(None, None, None)

        self.assertEqual(
            str(error),
            "An error ocurred in the Filesystem model.",
        )

        self.assertRegex(
            str(error),
            FilesystemError.regex_string(),
        )

    def test_program_base(self):
        error = ProgramError(None, None, None)

        self.assertEqual(
            str(error),
            "An error ocurred in the Program model.",
        )

        self.assertRegex(
            str(error),
            ProgramError.regex_string(),
        )

    def test_script_base(self):
        error = ScriptError(None, None)

        self.assertEqual(
            str(error),
            "An error ocurred in the Script model.",
        )

        self.assertRegex(
            str(error),
            ScriptError.regex_string(),
        )

    def test_query_base(self):
        error = QueryError(None)

        self.assertEqual(
            str(error),
            "There was an error in your query.",
        )

        self.assertRegex(
            str(error),
            QueryError.regex_string(),
        )
