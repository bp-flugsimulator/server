from django.test import TestCase

from frontend.errors import (
    FilesystemError,
    ProgramError,
)


class BaseErrorTests(TestCase):  # pylint: disable=unused-variable
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
