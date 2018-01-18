from channels import Group
from utils import Status


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
