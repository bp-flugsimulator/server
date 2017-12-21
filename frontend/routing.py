from channels.routing import route

from frontend.consumers import ws_notifications_connect, ws_notifications_receive, ws_notifications_disconnect, ws_rpc_connect, ws_rpc_disconnect

# handlers for websocket events
channel_routing = [
    route("websocket.connect", ws_rpc_connect, path=r"^/commands$"),
    route("websocket.disconnect", ws_rpc_disconnect, path=r"^/commands$"),
    route("websocket.connect", ws_notifications_connect),
    route("websocket.receive", ws_notifications_receive),
    route("websocket.disconnect", ws_notifications_disconnect),
]
