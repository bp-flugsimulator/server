"""
Base errors for all errors in this project.
"""

from utils import Status


class FsimError(Exception):
    """
    Base class for all errors.
    """

    def to_status(self):
        """
        Returns a Status object wich has the error as the payload.
        """
        return Status.err(str(self))

    @staticmethod
    def regex_string():
        """
        This functions returns a regex which corressponds to the format string. It can be
        used in a test case where the exception was send via a channel and is not known
        anymore.

        Returns
        -------
            An string which can be transformed into a regex expression
        """
        raise ValueError("This method is not implemented by the child class.")
