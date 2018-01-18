/* eslint-env browser*/
/* global $, Status */
/* export fsimWebsocket */
/*eslint no-console: ["error", { allow: ["log"] }] */

function fsimWebsocket(partialSocketEventHandler) {
    let socket = new WebSocket('ws://' + window.location.host + '/notifications');

    let handler = {
        get: function (target, name) {
            return name in target ?
                target[name] :
                function () { };
        }
    };

    let socketEventHandler = new Proxy(partialSocketEventHandler, handler);

    socket.onmessage = function (data) {
        let status = Status.from_json(data.data);
        console.log(status);

        if (status.is_ok()) {
            if (status.payload.slave_status != null) {
                // handle slave status updates
                switch (status.payload.slave_status) {
                    case 'connected':
                        socketEventHandler.slaveConnect(status.payload);
                        break;
                    case 'disconnected':
                        socketEventHandler.slaveDisconnect(status.payload);
                        break;
                    default:
                        notify('Warning message', 'Unknown slave_status received (' + JSON.stringify(status.payload.message) + ')', 'info');
                }
            } else if (status.payload.program_status != null) {
                // handle program status updates
                switch (status.payload.program_status) {
                    case 'started':
                        socketEventHandler.programStarted(status.payload);
                        break;
                    case 'finished':
                        socketEventHandler.programStopped(status.payload);
                        break;
                    default:
                        notify('Warning message', 'Unknown program_status received (' + JSON.stringify(status.payload.message) + ')', 'info');
                }
            } else if (status.payload.script_status != null) {
                // handle slave status updates
                switch (status.payload.script_status) {
                    case 'waiting_for_slaves':
                        socketEventHandler.scriptWaitForSlaves(status.payload);
                        break;
                    case 'next_step':
                        socketEventHandler.scriptNextStep(status.payload);
                        break;
                    case 'success':
                        socketEventHandler.scriptSuccess(status.payload);
                        break;
                    case 'error':
                        socketEventHandler.scriptError(status.payload);
                        break;
                    default:
                        notify('Warning message', 'Unknown script_status received (' + JSON.stringify(status.payload.message) + ')', 'info');
                }
            } else if (status.payload.message != null) {
                notify('Info message', JSON.stringify(status.payload.message), 'info');
            } else {
                notify('Unknown status message', 'The server responded with an unknown message type. (' + JSON.stringify(status.payload) + ')', 'warning');
            }
        } else {
            notify('Unknown message', JSON.stringify(status), 'danger');
        }
    };

    return socket;
}
