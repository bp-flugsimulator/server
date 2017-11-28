from channels import Group

# Connected to websocket.connect
def ws_add(message):
    # Accept the connection
    message.reply_channel.send({"accept": True})
    # Add to the chat group
    Group('notifications').add(message.reply_channel)

# Connected to websocket.receive
def ws_message(message):
    Group('notifications').send({
        "text": "WIP TODO",
    })

# Connected to websocket.disconnect
def ws_disconnect(message):
    Group('notifications').discard(message.reply_channel)
