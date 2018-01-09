socket = new WebSocket('ws://' + window.location.host + '/notifications');
socket.onmessage = function (data) {
    let status = Status.from_json(data.data);

    console.log(status)
    if (status.payload['slave_status'] != null) {
        // handle slave status updates

        let statusContainer = $('#slaveStatusContainer_' + status.payload['sid']);
        let startstopButton = $('#slaveStartStop_' + status.payload['sid']);

        switch (status.payload['slave_status']) {
            case 'connected':
                // swap status
                statusContainer.removeClass('fsim-status-error');
                statusContainer.addClass('fsim-status-success');

                // swap start and stop functions
                startstopButton.removeClass('start-slave');
                startstopButton.addClass('stop-slave');

                // set tooltip to Stop
                startstopButton.prop('title', 'Stops the client');

                break;
            case 'disconnected':
                // swap status
                statusContainer.removeClass('fsim-status-success');
                statusContainer.addClass('fsim-status-error');

                // swap start and stop functions
                startstopButton.removeClass('stop-slave');
                startstopButton.addClass('start-slave');

                // set tooltip to Start
                startstopButton.prop('title', 'Starts the client');

                break;
        }
    } else if (status.payload['program_status'] != null) {
        // handle program status updates

        let statusContainer = $('#programStatusContainer_' + status.payload['pid']);
        let startstopButton = $('#programStartStop_' + status.payload['pid']);

        switch (status.payload['program_status']) {
            case 'started':
                statusContainer.addClass('fsim-status-success');
                statusContainer.removeClass('fsim-status-error');

                startstopButton.prop('title', 'Stops the program');
                break;
            case 'finished':
                statusContainer.addClass('fsim-status-error');
                statusContainer.removeClass('fsim-status-success');

                startstopButton.prop('title', 'Starts the program');
                break;
        }
    } else {
        console.log("unknown");
        console.log(status.payload);
        $.notify({
            type: 'warning',
            message: 'received unknown response from server'
        });
    }
};
socket.onopen = function () {
    console.log('Websocket opened')
};
// Call onopen directly if socket is already open
if (socket.readyState === WebSocket.OPEN) socket.onopen();
