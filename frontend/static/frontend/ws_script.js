
var socket = new WebSocket('ws://' + window.location.host + '/notifications');
var socketEventHandler = {
    slavesConnected(payload) {
        notify('Slaves connected', 'All slaves have been connected to the server.', 'info');
    },
    programsDone(payload) {
        notify('Stage done', 'All program for this stage has been started. Going to the next.', 'info');
    },
    success(payload) {
        notify('Success', 'The script has been successfuly started.', 'success');
    },
    error(payload) {
        notify('Error', 'There was an error while running the script.', 'danger');
    },
};
socket.onmessage = function (data) {
    let status = Status.from_json(data.data);
    console.log(status);

    if (status.is_ok()) {
        if (status.payload['script_status'] != null) {
            // handle slave status updates
            switch (status.payload['script_status']) {
                case 'slaves_connected':
                    socketEventHandler.slavesConnected(status.payload);
                    break;
                case 'programs_done':
                    socketEventHandler.programsDone(status.payload);
                    break;
                case 'success':
                    socketEventHandler.success(status.payload);
                    break;
                case 'error':
                    socketEventHandler.error(status.payload);
                    break;
            }
        } else if (status.payload['message'] != null) {
            notify('Info message', JSON.stringify(status.payload['message']), 'info');
        } else {
            notify('Unknown status message', 'The server repsonded with an unknown message type. (' + JSON.stringify(status.payload) + ')', 'warning');
        }
    } else {
        notify('Unknown message', JSON.stringify(status), 'danger');
    }
};

// Call onopen directly if socket is already open
if (socket.readyState === WebSocket.OPEN) {
    socket.onopen();
}
