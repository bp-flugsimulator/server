"""
This module specifies which websockets are connected with which function.
"""
from channels.routing import route

from frontend.consumers import ws_notifications_connect, ws_notifications_receive,\
    ws_notifications_disconnect, ws_rpc_connect, ws_rpc_disconnect

# handlers for websocket events
channel_routing = [  # pylint: disable=C0103
    route(
        "websocket.connect",
        ws_rpc_connect,
        path=r"^/commands$",
    ),
    route(
        "websocket.disconnect",
        ws_rpc_disconnect,
        path=r"^/commands$",
    ),
    route(
        "websocket.connect",
        ws_notifications_connect,
        path=r"^/notifications$",
    ),
    route(
        "websocket.receive",
        ws_notifications_receive,
        path=r"^/notifications$",
    ),
    route(
        "websocket.disconnect",
        ws_notifications_disconnect,
        path=r"^/notifications$",
    ),
]
