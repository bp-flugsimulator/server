/* eslint-env browser*/
/* eslint no-use-before-define: ["error", { "functions": false }] */
/* eslint no-console: ["error", { allow: ["log"] }] */
/* global Status, notify */
/* exported fsimWebsocket */

/**
 *  Only class the given function if it exist in the object.
 *
 *  @param {Object} obj Where the function should called from.
 *  @param {String} fun Function name
 *  @param {Object} argument One argument for the function call
 */
function callMaybe(obj, fun, arg) {
    if (typeof(obj[fun]) !== 'undefined') {
        obj[fun].call(obj, arg);
    }
}

function fsimWebsocket(socketEventHandler) {
    let socket = new WebSocket('ws://' + window.location.host + '/notifications');

    socket.onopen = function () {
        console.log('Websocket open');
    };

    socket.onerror = function (error) {
        console.log('Websocket error: ' + error);
    };

    socket.onclose = function () {
        console.log('Websocket closed');
    };

    socket.onmessage = function (data) {
        let status = Status.from_json(data.data);
        console.log(status);

        if (status.is_ok()) {
            if (status.payload.slave_status != null) {
                // handle slave status updates
                switch (status.payload.slave_status) {
                    case 'connected':
                        callMaybe(socketEventHandler, 'slaveConnect', status.payload);
                        break;
                    case 'disconnected':
                        callMaybe(socketEventHandler, 'slaveDisconnect', status.payload);
                        break;
                    default:
                        notify('Warning message', 'Unknown slave_status received (' + JSON.stringify(status.payload.message) + ')', 'info');
                }
            } else if (status.payload.program_status != null) {
                // handle program status updates
                switch (status.payload.program_status) {
                    case 'started':
                        callMaybe(socketEventHandler, 'programStarted', status.payload);
                        break;
                    case 'finished':
                        callMaybe(socketEventHandler, 'programStopped', status.payload);
                        break;
                    default:
                        notify('Warning message', 'Unknown program_status received (' + JSON.stringify(status.payload.message) + ')', 'info');
                }
            } else if (status.payload.script_status != null) {
                // handle slave status updates
                switch (status.payload.script_status) {
                    case 'waiting_for_slaves':
                        callMaybe(socketEventHandler, 'scriptWaitForSlaves', status.payload);
                        break;
                    case 'next_step':
                        callMaybe(socketEventHandler, 'scriptNextStep', status.payload);
                        break;
                    case 'success':
                        callMaybe(socketEventHandler, 'scriptSuccess', status.payload);
                        break;
                    case 'error':
                        callMaybe(socketEventHandler, 'scriptError', status.payload);
                        break;
                    default:
                        notify('Unknown message', 'Unknown script_status received (' + JSON.stringify(status.payload.message) + ')', 'info');
                }
            } else if (status.payload.log != null) {
                // handle program log update
                socketEventHandler.programUpdateLog(status.payload);
            } else if (status.payload.filesystem_status != null) {
                switch (status.payload.filesystem_status) {
                    case 'moved':
                        callMaybe(socketEventHandler, 'filesystemMoved', status.payload);
                        break;
                    case 'restored':
                        callMaybe(socketEventHandler, 'filesystemRestored', status.payload);
                        break;
                    case 'error':
                        callMaybe(socketEventHandler, 'filesystemError', status.payload);
                        break;
                    default:
                        notify('Unknown message', 'Unknown filesystem_status received (' + JSON.stringify(status.payload.message) + ')', 'info');
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
