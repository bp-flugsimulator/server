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
def ws_add_rpc_commands(message):
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


# Connected to websocket.disconnect
@channel_session
def ws_rpc_disconnect(message):
    query = SlaveModel.objects.filter(
        ip_address=message.channel_session['ip_address'])

    if query:
        slave = query.first()
        Group('clients').discard(message.reply_channel)
        Group('client_{}'.format(slave.id)).discard(message.reply_channel)
        slave.slavestatus.delete()

        logger.info("Client with ip {} disconnected from /commands!".format(
            message.channel_session['ip_address']))

# Connected to websocket.connect
def ws_notifications_add(message):
    # Add to the notification group
    Group('notifications').add(message.reply_channel)
    # Accept the connection
    message.reply_channel.send({"accept": True})


# Connected to websocket.receive
def ws_notifications_receive(message):
    """
    Handels incomming messages on /.
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
                'Exception occured while handeling an incomming request on /commands \n{}'.
                format(err), 'red'))


# Connected to websocket.disconnect
def ws_notifications_disconnect(message):
    Group('notifications').discard(message.reply_channel)
