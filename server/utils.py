"""
This module contains utility classes.
"""
from django.http.response import HttpResponse
from channels import Group

from utils import Status, Command
from utils.typecheck import ensure_type
from .errors import FsimError


class StatusResponse(HttpResponse):
    """
    Override of the standard HttpResponse
    so a Status object from the utils
    library can be used.
    """

    def __init__(self, data, **kwargs):
        """
        Init Method
        :param data: a status object
        :param kwargs: standard kwargs for HttpResponse
        """
        if data and not isinstance(data, Status) and not isinstance(
                data, FsimError):
            raise TypeError('Only Status objects are allowed here')

        kwargs.setdefault('content_type', 'application/json')

        if isinstance(data, FsimError):
            data = data.to_status()

        data = data.to_json()
        super(StatusResponse, self).__init__(content=data, **kwargs)

    @classmethod
    def ok(cls, payload, **kwargs):
        """
        Shorthand for StatusResponse(Status.ok(payload))

        Arguments
        ---------
            payload: Payload for Status object
            **kwargs: arguments for HttpResponse

        Returns
        -------
            StatusResponse object with 'ok' in Status
        """
        return cls(Status.ok(payload), **kwargs)

    @classmethod
    def err(cls, payload, **kwargs):
        """
        Shorthand for StatusResponse(Status.err(payload))

        Arguments
        ---------
            payload: Payload for Status object
            **kwargs: arguments for HttpResponse

        Returns
        -------
            StatusResponse object with 'err' in Status
        """
        return cls(Status.err(payload), **kwargs)


def notify(message):
    """
    Sending the given `message` to the notification channel, inidcating that
    the message is not an error.

    Parameters
    ----------
        message: JSON object
            This message is send to the web interface with an Status.ok()
            wrapped around.
    """
    Group('notifications').send({'text': Status.ok(message).to_json()})


def notify_err(message):
    """
    Sending the given `message` to the notification channel. Indicating that
    the message is an error message.

    Parameters
    ----------
        message: JSON object
            This message is send to the web interface with an Status.err()
            wrapped around.
    """
    Group('notifications').send({'text': Status.err(message).to_json()})


def notify_slave(command, slave_id):
    """
    Sending the given `message` to the notification channel. Indicating that
    the message is an error message.

    Parameters
    ----------
        message: JSON object
            This message is send to the web interface with an Status.err()
            wrapped around.
    """
    ensure_type("command", command, Command)
    Group('client_' + str(slave_id)).send({'text': command.to_json()})
