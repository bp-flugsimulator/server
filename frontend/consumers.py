from channels import Group
from .models import SlaveStatus as SlaveStatusModel, Slave as SlaveModel, Program as ProgramModel, ProgramStatus as ProgramStatusModel
from utils import Command, Status
from channels.sessions import channel_session
from termcolor import colored

# import the logging library
import logging

# Get an instance of a logger
logger = logging.getLogger('django.request')


def notify(message):
    Group('notifications').send({'text': Status.ok(message).to_json()})


def notify_err(message):
    Group('notifications').send({'text': Status.err(message).to_json()})


def handle_execute_answer(status):
    program_status = ProgramStatusModel.objects.get(command_uuid=status.uuid)
    program = program_status.program

    logger.info(
        "Received answer on execute request of function {} from {}.".format(
            program.name, program.slave.name))

    if status.is_ok():
        # update return code
        program_status.code = status.payload['result']
        logger.info("Saved status of {} with code {}.".format(
            program.name, program_status.code))
    else:
        # Report exception to webinterface
        notify_err('An Exception occured while trying to execute {}'.format(
            program.name))
        logger.info(
            colored(
                'Following exeption occured on the client while executing {}: \n {}'.
                format(program.name, status.payload['result']), 'red'))

    # update status
    program_status.running = False
    program_status.save()
    # tell webinterface that the program has ended
    notify({
        'program_status': 'finished',
        'pid': str(program.id),
        'code': status.payload['result']
    })


def handle_online_answer(status):
    slave_status = SlaveStatusModel.objects.get(command_uuid=status.uuid)

    slave = slave_status.slave

    if status.is_ok():
        slave_status.online = True
        slave_status.save()

        # tell webinterface that the client has been connected
        notify({'slave_status': 'connected', 'sid': str(slave.id)})
    else:
        # notify the webinterface
        notify_err('An error occured while connecting to client {}!'.format(
            slave.name))

        logger.info(
            colored(
                'Following exeption occured on the client {} while handeling an "online-request": \n {}'.
                format(slave.name, status.payload['result']), 'red'))


@channel_session
def ws_rpc_connect(message):
    """
    Handels websockets.connect requests of '/commands'.
    Connections only get accepted if the ip of the sender is the ip of a known client.
    Adds the reply_channel to the groups 'clients' and 'client_$slave.id' and sends an
    online request to the client.

    Arguments
    ---------
        message: channels.message.Message that contains the connection request  on /commands

    """
    ip_address, port = message.get('client')
    message.channel_session['ip_address'] = ip_address
    query = SlaveModel.objects.filter(ip_address=ip_address)

    if query:
        # Accept the connection
        message.reply_channel.send({"accept": True})
        logger.info("client connected with ip {} on port {}".format(
            ip_address, port))
        # Add to the command group
        slave = query.first()
        Group('clients').add(message.reply_channel)
        Group('client_{}'.format(slave.id)).add(message.reply_channel)

        # send/save online request
        cmd = Command(method='online')
        SlaveStatusModel(slave=slave, command_uuid=cmd.uuid).save()
        Group('client_{}'.format(slave.id)).send({'text': cmd.to_json()})

        # log
        logger.info("send online request to {}".format(slave.name))
    else:
        logger.info(
            colored("Rejecting unknown client with ip {}!".format(ip_address),
                    'red'))
        message.reply_channel.send({"accept": False})


@channel_session
def ws_rpc_disconnect(message):
    """
    Handels websockets.disconnect requests of '/commands'.
    Only disconnects known clients.
    Removes the reply_channel from 'clients' and 'clients_$slave.id' and deletes the SlaveStatus entry in the database

    Arguments
    ---------
        message: channels.message.Message that contains the disconnect request  on /commands

    """
    query = SlaveModel.objects.filter(
        ip_address=message.channel_session['ip_address'])

    if query:
        slave = query.first()
        Group('clients').discard(message.reply_channel)
        Group('client_{}'.format(slave.id)).discard(message.reply_channel)
        slave.slavestatus.online = False
        slave.slavestatus.save()

        # if a slave disconnects all programs stop
        for program in ProgramModel.objects.filter(slave=slave):
            notify({
                'program_status': 'finished',
                'pid': program.id,
                'code': 'Status',
            })
            if ProgramStatusModel.objects.filter(program=program).exists():
                ProgramStatusModel.objects.get(program=program).delete()

        # tell the webinterface that the client has disconnected
        notify({'slave_status': 'disconnected', 'sid': str(slave.id)})

        logger.info("Client with ip {} disconnected from /commands!".format(
            message.channel_session['ip_address']))


def ws_notifications_connect(message):
    """
    Handels websockets.connect requests of '/notifications'.
    Connections only get accepted if the ip of the sender is the ip of a known slave.
    Adds the reply_channel to the group 'notifications'

    Arguments
    ---------
        message: channels.message.Message that contains the connection request  on '/'.

    """
    # Add to the notification group
    Group('notifications').add(message.reply_channel)
    # Accept the connection
    message.reply_channel.send({"accept": True})


def ws_notifications_receive(message):
    """
    Handels websockets.receive requests of '/notifications'.
    Connections only get accepted if the ip of the sender is the ip of a known slave.

    If the status contains the result of a boottime request a corresponding SlaveStatus
    will be created in in the database.

    If the status contains the result of an execute request the corresponding ProgramStatus will
    get updated in the database and the message gets republished to the 'notifications' group.

    Arguments
    ---------
        message: channels.message.Message that contains a Status in the 'text' field

    """

    try:
        status = Status.from_json(message.content['text'])
        if status.payload['method'] == 'online':
            handle_online_answer(status)
        elif status.payload['method'] == 'execute':
            handle_execute_answer(status)
        else:
            logger.info(
                colored('Client send answer from unknown function {}.'.format(
                    status.payload['method']), 'red'))
    except Exception as err:
        logger.info(
            colored(
                'Exception occurred while handeling an incoming request on /commands \n{}'.
                format(err), 'red'))


def ws_notifications_disconnect(message):
    """
    Handels websockets.disconnected requests of '/notifications'.
    Removes the reply_channel from the 'notifications' group

    Arguments
    ---------
        message: channels.message.Message that contains the disconnect request  on '/'

    """

    Group('notifications').discard(message.reply_channel)
