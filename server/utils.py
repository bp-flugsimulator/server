"""
This module contains utility classes.
"""
from django.http.response import HttpResponse

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
