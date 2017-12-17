from channels import Group
from .models import SlaveStatus as SlaveStatusModel, Slave as SlaveModel, Program as ProgramModel
from utils import Command, Status
from channels.sessions import channel_session


from datetime import datetime

# Connected to websocket.connect
def ws_add(message):
    # Accept the connection
    message.reply_channel.send({"accept": True})
    # Add to the notification group
    Group('notifications').add(message.reply_channel)

@channel_session
def ws_add_rpc_commands(message):
    ip_address, port = message.get('client')
    message.channel_session['ip_address'] = ip_address
    print("Connected to notification channel with Ip: {}".format(ip_address))
    query = SlaveModel.objects.filter(ip_address=ip_address)

    if query.count() == 1:
        # Accept the connection
        message.reply_channel.send({"accept": True})
        # Add to the command group
        slave =  query.first()
        Group('commands').add(message.reply_channel)
        Group('commands_{}'.format(slave.id)).add(
            message.reply_channel)

        # send boottime request
        Group('commands_{}'.format(slave.id)).send(
            {
            'text':
                Command(
                    method="boottime",
                    sid=slave.id
                ).to_json()
            }
        )
        message.reply_channel.send({"accept": True})
    else:
        message.reply_channel.send({"accept": False})


# Connected to websocket.receive
def ws_message(message):
    """
    Handels incomming messages on /.
    """
    status = Status.from_json(message.content['text'])
    if status.is_ok():
        if status.payload['method'] == 'boottime':
            slave = SlaveModel.objects.get(id=status.payload['sid'])
            boottime = datetime.strptime(status.payload['boottime'],'%Y-%m-%d %H:%M:%S')
            SlaveStatusModel(slave=slave,boottime=boottime).save()
            message.reply_channel.send({"accept": True})
        elif status.payload['method'] == 'execute':
            program_status = ProgramModel.objects.get(id=status.payload['pid']).programstatus
            program_status.code = status.payload['code']
            program_status.stopped = datetime.now()
        else:
            message.reply_channel.send({"accept": False})
    else:
        message.reply_channel.send({"accept": False})

# Connected to websocket.disconnect
def ws_disconnect(message):
    Group('notifications').discard(message.reply_channel)

    
# Connected to websocket.disconnect
@channel_session
def ws_rpc_disconnect(message):
    Group('commands').discard(message.reply_channel)
    Group('commands_{}'.format(message.channel_session['ip_address'])).discard(message.reply_channel)
    SlaveModel.objects.get(ip_address=message.channel_session['ip_address']).slavestatus.delete()


