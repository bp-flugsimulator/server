from channels.routing import route

from frontend.consumers import ws_notifications_add, ws_notifications_receive, ws_notifications_disconnect, ws_add_rpc_commands, ws_rpc_disconnect

# handlers for websocket events
channel_routing = [
    route("websocket.connect", ws_add_rpc_commands, path=r"^/commands$"),
    route("websocket.disconnect", ws_rpc_disconnect, path=r"^/commands$"),
    route("websocket.connect", ws_notifications_add),
    route("websocket.receive", ws_notifications_receive),
    route("websocket.disconnect", ws_notifications_disconnect),
]
