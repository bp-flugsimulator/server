"""
Test cases for frontend.
"""
import unittest

from django.test import TestCase
from server.errors import FsimError

from utils import Status
from utils.typecheck import ensure_type

def assertStatusRegex(self, regex_status, status_object):
    """
    Asserts that status_object.payload matches the regex_status.payload and that both
    have the same status type.

    regex_status.payload can be either an FsimError or an regex expression (as a
    string).

    Exceptions
    ----------
        TypeException: if regex_status or status_object are not Status objects or if the payload is not a string.
    """
    ensure_type("regex_status", regex_status, Status)
    ensure_type("status_object", status_object, Status)

    ensure_type("status_object.payload", status_object.payload, str)
    ensure_type(
        "regex_status.payload",
        status_object.payload,
        str,
        FsimError,
        FsimError.__class__,
    )

    if isinstance(regex_status.payload, FsimError) or isinstance(
            regex_status.payload, FsimError.__class__):
        regex_string = regex_status.payload.regex_string()
    elif isinstance(regex_status.payload, str):
        regex_string = regex_status.payload

    self.assertEqual(regex_status.status, status_object.status)
    self.assertRegex(status_object.payload, regex_string)

class StatusTestCase(TestCase):
    """
    Provides functions to compare status objects.
    """

    assertStatusRegex = assertStatusRegex

class SchedulerTestCase(unittest.TestCase):
    """
    Testcase for the `Scheudler` which provides an addiational comparison.
    """

    assertStatusRegex = assertStatusRegex

    def assertStatusSet(self, first, second):
        """
        Asserts that two arrays of `Status` are equal by the defintion of a
        set.

        Arguments
        ---------
            first: list of Status
                First operand
            second: list of Status
                Second operand

        Raises
        ------
            AssertionError:
                If an element is found which does not belong the the list.
        """

        self.assertTrue(len(first), len(second))

        for x in first:
            if x in second:
                second.remove(x)

        if len(second) > 0:
            raise AssertionError(first, second)

