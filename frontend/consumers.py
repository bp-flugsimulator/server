from channels import Group

# Connected to websocket.connect
def ws_add(message): #pragma: no cover
    # Accept the connection
    message.reply_channel.send({"accept": True})
    # Add to the chat group
    Group('notifications').add(message.reply_channel)

def ws_add_rpc_commands(message):
    # Accept the connection
    message.reply_channel.send({"accept": True})
    # Add to the chat group
    Group('commands').add(message.reply_channel)

# Connected to websocket.receive
def ws_message(message): #pragma: no cover
    Group('notifications').send({
        "text": "WIP TODO",
    })

# Connected to websocket.disconnect
def ws_disconnect(message): #pragma: no cover
    Group('notifications').discard(message.reply_channel)

# Connected to websocket.disconnect
def ws_rpc_disconnect(message): #pragma: no cover
    Group('commands').discard(message.reply_channel)
