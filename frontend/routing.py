from channels.routing import route

from frontend.consumers import ws_add, ws_message, ws_disconnect, ws_add_rpc_commands, ws_rpc_disconnect

# handlers for websocket events
channel_routing = [
    route("websocket.connect", ws_add_rpc_commands, path=r"^/commands$"),
    route("websocket.connect", ws_add),
    route("websocket.receive", ws_message),
    route("websocket.disconnect", ws_rpc_disconnect, path=r"^/commands$"),
    route("websocket.disconnect", ws_disconnect),
]
