from channels import Group
from .models import Slave as SalveModel


# Connected to websocket.connect
def ws_add(message):
    # Accept the connection
    message.reply_channel.send({"accept": True})
    # Add to the chat group
    Group('notifications').add(message.reply_channel)


def ws_add_rpc_commands(message):
    ip_address, port = message.get('client')
    print("Connected to notification channel with Ip: {}".format(ip_address))
    query = SalveModel.objects.filter(ip_address=ip_address)

    if query.count() == 1:
        # Accept the connection
        message.reply_channel.send({"accept": True})
        # Add to the chat group
        Group('commands').add(message.reply_channel)
        Group('commands_{}'.format(query.first().id)).add(
            message.reply_channel)
    else:
        message.reply_channel.send({"accept": False})


# Connected to websocket.receive
def ws_message(message):
    Group('notifications').send({
        "text": "WIP TODO",
    })


# Connected to websocket.disconnect
def ws_disconnect(message):
    Group('notifications').discard(message.reply_channel)

    
# Connected to websocket.disconnect
def ws_rpc_disconnect(message):
    Group('commands').discard(message.reply_channel)
