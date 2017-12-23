from channels import Group
from .models import SlaveStatus as SlaveStatusModel, Slave as SlaveModel, Program as ProgramModel
from utils import Command, Status
from channels.sessions import channel_session
from datetime import datetime
from django.utils import timezone
from termcolor import colored

# import the logging library
import logging

# Get an instance of a logger
logger = logging.getLogger('django.request')


@channel_session
def ws_rpc_connect(message):
    """
    Handels websockets.connect requests of '/commands'.
    Connections only get accepted if the ip of the sender is the ip of a known client.
    Adds the reply_channel to the groups 'clients' and 'client_$slave.id' and sends a
    boottime request to the client.

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

        logger.info("send boottime request to {}".format(slave.name))
        # send boottime request
        Group('client_{}'.format(slave.id)).send({
            'text':
            Command(method="boottime", sid=slave.id).to_json()
        })
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
        slave.slavestatus.delete()

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
        if status.is_ok():
            if status.payload['method'] == 'boottime':
                slave = SlaveModel.objects.get(id=status.payload['sid'])
                logger.info(
                    "Received answer on boottime request from {}.".format(
                        slave.name))
                boottime = datetime.strptime(status.payload['boottime'],
                                             '%Y-%m-%d %H:%M:%S')
                SlaveStatusModel(slave=slave, boottime=boottime).save()
                logger.info("Saved status of {} with boottime {}".format(
                    slave.name, boottime))

            elif status.payload['method'] == 'execute':
                program = ProgramModel.objects.get(id=status.payload['pid'])

                logger.info(
                    "Received answer on execute request of function {} from {}.".
                    format(program.name, program.slave.name))

                program_status = program.programstatus
                program_status.code = status.payload['code']
                program_status.stopped = timezone.now()
                program_status.save()

                logger.info("Saved status of {} with code {}.".format(
                    program.name, program_status.code))

                # pass on message to webinterface
                Group('notifications').send({'text': message.content['text']})
            else:
                logger.info(
                    colored(
                        'Client send answer from unknown function {}.'.format(
                            status.payload['method']), 'red'))
        else:
            logger.info(
                colored('Client answered with error: {}'.format(
                    status.payload), 'red'))
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
