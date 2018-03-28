"""
This module contains all functions that handle requests on websockets.
"""
import logging
import traceback
import os

from channels import Group
from channels.sessions import channel_session

from utils import Command, Status, FormatError

from .models import (
    Slave as SlaveModel,
    Program as ProgramModel,
    ProgramStatus as ProgramStatusModel,
    Filesystem as FilesystemModel,
)

from server.utils import notify_err, notify

# Get an instance of a logger
LOGGER = logging.getLogger('fsim.websockets')


def select_method(status):
    """
    Selects a handler for the incoming message by checking the name with the
    function_handle_table.

    Parameters
    ----------
        status: Status object

    """
    LOGGER.debug(dict(status))

    function_handle_table = {
        'online': handle_online,
        'execute': handle_execute,
        'filesystem_move': handle_filesystem_moved,
        'filesystem_restore': handle_filesystem_restored,
        'chain_execution': handle_chain_execution,
        'get_log': handle_get_log,
    }

    if status.payload['method'] in function_handle_table:
        function_handle_table[status.payload['method']](status)

        # notify the scheduler that the status has changed
        FSIM_CURRENT_SCHEDULER.notify()
    else:
        LOGGER.warning(
            'Client send answer from unknown function %s.',
            status.payload['method'],
        )


def handle_chain_execution(status):
    """
    Handles an incoming message on '/notification' that
    is an answer to an 'chain_execution' request on a slave

    Parameters
    ----------
    status: Status
        The statusobject that was send by the slave
    """
    LOGGER.info("Handle chain execution %s", dict(status))

    if status.is_ok():
        LOGGER.info("chain_execution results: %s", dict(status))

        for result in status.payload["result"]:
            select_method(Status(**result))
    else:
        LOGGER.error(
            "Received Status.err for chain_execution, but this function can not raise errors. (payload: %s)",
            status.payload,
        )


def handle_filesystem_restored(status):
    """
    Handles an incoming message on '/notification' that
    is an answer to an 'filesystem_restore' request on a slave

    Parameters
    ----------
    status: Status
        The statusobject that was send by the slave
    """
    LOGGER.info("Handle filesystem restored %s", dict(status))

    try:
        file_ = FilesystemModel.objects.get(command_uuid=status.uuid)
    except FilesystemModel.DoesNotExist:
        LOGGER.warning(
            "A filesystem restored with id %s, but is not in the database.",
            status.uuid,
        )
        return

    if status.is_ok():
        file_.hash_value = ""
        file_.error_code = ""
        file_.save()

        LOGGER.info(
            "Restored filesystemsystem %s.",
            file_.name,
        )

        notify({
            'filesystem_status': 'restored',
            'fid': str(file_.id),
        })
    else:
        file_.error_code = status.payload['result']
        file_.save()

        notify({
            'filesystem_status': 'error',
            'error_code': status.payload['result'],
            'fid': str(file_.id),
        })


def handle_filesystem_moved(status):
    """
    Handles an incoming message on '/notification' that
    is an answer to an 'filesystem_move' request on a slave

    Parameters
    ----------
    status: Status
        The statusobject that was send by the slave
    """
    LOGGER.info("Handle filesystem moved %s", dict(status))

    try:
        file_ = FilesystemModel.objects.get(command_uuid=status.uuid)
    except FilesystemModel.DoesNotExist:
        LOGGER.warning(
            "A filesystem moved with id %s, but is not in the database.",
            status.uuid,
        )
        return

    if status.is_ok():
        file_.hash_value = status.payload['result']
        file_.error_code = ""
        file_.save()

        LOGGER.info(
            "Saved filesystem %s with hash value %s.",
            file_.name,
            file_.hash_value,
        )

        notify({
            'filesystem_status': 'moved',
            'fid': str(file_.id),
        })

    else:
        file_.error_code = status.payload['result']
        file_.hash_value = ""
        file_.save()

        LOGGER.error(
            "Error while moving filesystem: %s",
            status.payload['result'],
        )

        notify({
            'filesystem_status': 'error',
            'error_code': status.payload['result'],
            'fid': str(file_.id),
        })


def handle_execute(status):
    """
    Handles an incoming message on '/notification' that
    is an answer to an 'execute' request on a slave

    Parameters
    ----------
    status: Status
        The statusobject that was send by the slave
    """
    LOGGER.info("Handle program execute %s", dict(status))

    try:
        program_status = ProgramStatusModel.objects.get(
            command_uuid=status.uuid)
        program = program_status.program
    except ProgramStatusModel.DoesNotExist:
        LOGGER.warning(
            "A program finished with id %s, but is not in the database.",
            status.uuid,
        )
        return

    LOGGER.info(
        "Received answer on execute request of function %s from %s.",
        program.name,
        program.slave.name,
    )

    if status.is_ok():
        LOGGER.info(
            "Saved status of %s with code %s.",
            program.name,
            program_status.code,
        )
    else:
        LOGGER.error(
            'Exception in occurred client while executing %s: %s %s',
            program.name,
            os.linesep,
            status.payload['result'],
        )

    # update status
    program_status.code = status.payload['result']
    program_status.running = False
    program_status.save()

    # tell webinterface that the program has ended
    notify({
        'program_status': 'finished',
        'pid': str(program.id),
        'code': status.payload['result']
    })


def handle_online(status):
    """
    Handles an incoming message on '/notification' that
    is an answer to an 'online' request on a slave

    Parameters
    ----------
    status: Status
        The statusobject that was send by the slave
    """
    LOGGER.info("Handle slave online %s", dict(status))

    try:
        slave = SlaveModel.objects.get(command_uuid=status.uuid)
    except SlaveModel.DoesNotExist:
        LOGGER.warning(
            "Slaves online request with uuid %s, was not asked for it.",
            status.uuid,
        )
        return

    if status.is_ok():
        slave.online = True
        slave.save()

        # tell webinterface that the client has been connected
        notify({'slave_status': 'connected', 'sid': str(slave.id)})
        LOGGER.info(
            'Slave %s has connected to the master',
            slave.name,
        )
    else:
        # notify the webinterface
        notify_err('An error occurred while connecting to client {}!'.format(
            slave.name))

        LOGGER.error(
            'Exception occurred in client %s (online-request): %s %s',
            slave.name,
            os.linesep,
            status.payload['result'],
        )


def handle_get_log(status):

    LOGGER.info("Handle log get %s", dict(status))

    if status.is_ok():
        try:
            program_status = ProgramStatusModel.objects.get(
                command_uuid=status.payload['result']['uuid'])
            program = program_status.program
        except ProgramStatusModel.DoesNotExist:
            notify_err('Received log from unknown program!')
            LOGGER.warning(
                "A log from a programm with id %s has arrived, but is not in the database.",
                status.uuid,
            )
            return

        LOGGER.info(
            "Received answer on get_log request of program %s on %s.",
            program.name,
            program.slave.name,
        )

        notify({
            'log': status.payload['result']['log'],
            'pid': str(program.id)
        })
        LOGGER.info("Send log of %s to the webinterface", program.name)
    else:
        notify_err('An error occured while reading a log file!')

        LOGGER.error(
            'Exception occurred (get_log-request): %s %s',
            os.linesep,
            status.payload['result'],
        )


@channel_session
def ws_rpc_connect(message):
    """
    Handels websockets.connect requests of '/commands'. Connections only get
    accepted if the ip of the sender is the ip of a known client. Adds the
    reply_channel to the groups 'clients' and 'client_$slave.id' and sends an
    online request to the client.

    Arguments
    ---------
    message: channels.message.Message that contains the connection request  on
    /commands

    """
    ip_address, port = message.get('client')
    message.channel_session['ip_address'] = ip_address
    try:
        slave = SlaveModel.objects.get(ip_address=ip_address)

        # Accept the connection
        message.reply_channel.send({"accept": True})

        LOGGER.info(
            "client connected with ip %s on port %s",
            ip_address,
            port,
        )

        # Add to the command group
        Group('client_{}'.format(slave.id)).add(message.reply_channel)
        LOGGER.debug('Added client to command group client_%s', slave.id)

        cmd = Command(method='online')

        # send/save online request
        slave.command_uuid = cmd.uuid
        slave.save()
        Group('client_{}'.format(slave.id)).send({'text': cmd.to_json()})
        LOGGER.info("send online request to %s", slave.name)

    except SlaveModel.DoesNotExist:
        LOGGER.error("Rejecting unknown client with ip %s!", ip_address)
        message.reply_channel.send({"accept": False})


def ws_rpc_receive(message):
    """
    Handels websockets.receive requests of '/Commands'. Connections only
    get accepted if the ip of the sender is the ip of a known slave.

    If the status contains the result of a boottime request a corresponding
    online will be set in SlaveModel.

    If the status contains the result of an execute request the corresponding
    ProgramStatus will get updated in the database and the message gets
    republished to the 'notifications' group.

    Arguments
    ---------
    message: channels.message.Message that contains a Status in the 'text' field

    """
    try:
        try:
            status = Status.from_json(message.content['text'])
        except ValueError as err:
            LOGGER.error(
                "Error while parsing json. (cause: %s)",
                str(err),
            )
            return
        select_method(status)
    except FormatError as err:
        LOGGER.error(
            "Could not parse Status from incoming request. (cause: %s)",
            str(err),
        )
    except KeyError:
        LOGGER.error("No content['text'] in received message.")


@channel_session
def ws_rpc_disconnect(message):
    """
    Handels websockets.disconnect requests of '/commands'. Only disconnects
    known clients. Removes the reply_channel from 'clients' and
    'clients_$slave.id' and sets online to False.

    Arguments
    ---------
    message: channels.message.Message that contains the disconnect request  on
    /commands

    """

    try:
        slave = SlaveModel.objects.get(
            ip_address=message.channel_session['ip_address'])

        Group('client_{}'.format(slave.id)).discard(message.reply_channel)

        slave.online = False
        slave.command_uuid = None

        slave.save()

        # if a slave disconnects all programs stop
        for program in ProgramModel.objects.filter(slave=slave):
            if ProgramStatusModel.objects.filter(program=program).exists():
                ProgramStatusModel.objects.get(program=program).delete()

        # tell the webinterface that the client has disconnected
        notify({'slave_status': 'disconnected', 'sid': str(slave.id)})

        # notify the scheduler that status has change
        FSIM_CURRENT_SCHEDULER.notify()

        LOGGER.info(
            "Client with ip %s disconnected from /commands!",
            message.channel_session['ip_address'],
        )

    except SlaveModel.DoesNotExist:
        LOGGER.error(
            "Disconnected client is not in database. (with IP %s)",
            message.channel_session['ip_address'],
        )


def ws_logs_connect(message):
    """
    Handels websockets.connect requests of '/notifications'.
    Adds the reply_channel to the group 'notifications'

    Arguments
    ---------
    message: channels.message.Message that contains the connection request  on
    '/notifications'.
    """

    # Accept the connection
    message.reply_channel.send({"accept": True})


def ws_logs_receive(message):
    """
    Handels websockets.receive requests of '/logs'. And forwards the content to
    the 'notifications' group. Every request gets acknowledged.

    Arguments
    ---------
    message: channels.message.Message that contains a logfile
    """
    Group('notifications').send({'text': message.content['text']})
    message.reply_channel.send({'text': 'ack'})


def ws_notifications_connect(message):
    """
    Handels websockets.connect requests of '/notifications'.
    Adds the reply_channel to the group 'notifications'

    Arguments
    ---------
    message: channels.message.Message that contains the connection request  on
    '/notifications'.
    """
    Group('notifications').add(message.reply_channel)
    message.reply_channel.send({"accept": True})


def ws_notifications_disconnect(message):
    """
    Handels websockets.disconnected requests of '/notifications'. Removes the
    reply_channel from the 'notifications' group

    Arguments
    ---------
    message: channels.message.Message that contains the disconnect request  on
    '/notifications'.
    """
    Group('notifications').discard(message.reply_channel)
