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
