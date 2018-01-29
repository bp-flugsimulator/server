"""
This module contains utility classes.
"""
from django.http.response import HttpResponse
from channels import Group

from utils.status import Status


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
        if data and not isinstance(data, Status):
            raise TypeError('Only Status objects are allowed here')
        kwargs.setdefault('content_type', 'application/json')
        data = data.to_json()
        super(StatusResponse, self).__init__(content=data, **kwargs)


def notify(message):
    """
    Sends a Status.ok with the given message
    on the 'notifications' channel

    Parameters
    ----------
    message: json serializable
        the message that is going to be send
    """
    Group('notifications').send({'text': Status.ok(message).to_json()})


def notify_err(message):
    """
    Sends a Status.err with the given message
    on the 'notifications' channel

    Parameters
    ----------
    message: json serializable
        the message that is going to be send
    """
    Group('notifications').send({'text': Status.err(message).to_json()})
