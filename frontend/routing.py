from channels.routing import route

from frontend.consumers import ws_add, ws_message, ws_disconnect

# handlers for websocket events
channel_routing = [
    route("websocket.connect", ws_add),
    route("websocket.receive", ws_message),
    route("websocket.disconnect", ws_disconnect),
]
