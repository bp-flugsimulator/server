"""
This module specifies which websockets are connected with which function.
"""
from channels.routing import route

from frontend.consumers import (
    ws_notifications_connect,
    ws_notifications_disconnect,
    ws_rpc_connect,
    ws_rpc_receive,
    ws_rpc_disconnect,
    ws_logs_connect,
    ws_logs_receive,
)

# handlers for websocket events
channel_routing = [  # pylint: disable=C0103
    route(
        "websocket.connect",
        ws_rpc_connect,
        path=r"^/commands$",
    ),
    route(
        "websocket.receive",
        ws_rpc_receive,
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
        "websocket.disconnect",
        ws_notifications_disconnect,
        path=r"^/notifications$",
    ),
    route(
        "websocket.connect",
        ws_logs_connect,
        path=r"^/logs$",
    ),
    route(
        "websocket.receive",
        ws_logs_receive,
        path=r"^/logs$",
    ),
]
