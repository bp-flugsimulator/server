/* eslint-env browser*/
/* global $, Status */

var socket = new WebSocket('ws://' + window.location.host + '/notifications');

socket.onmessage = function (data) {
    let status = Status.from_json(data.data);
    console.log(status);

    if (status.is_ok()) {
        if (status.payload['slave_status'] != null) {
            // handle slave status updates

            let statusContainer = $('#slaveStatusContainer_' + status.payload['sid']);
            let statusTab = $('#slaveTab' + status.payload['sid']);
            let startstopButton = $('#slaveStartStop_' + status.payload['sid']);

            switch (status.payload['slave_status']) {
                case 'connected':
                    // swap status
                    statusContainer.removeClass('fsim-status-error');
                    statusContainer.addClass('fsim-status-success');

                    statusTab.removeClass('fsim-status-error');
                    statusTab.addClass('fsim-status-success');

                    // swap start and stop functions
                    startstopButton.removeClass('start-slave');
                    startstopButton.addClass('stop-slave');

                    // set tooltip to Stop
                    startstopButton.prop('text', 'STOP');

                    break;
                case 'disconnected':
                    // swap status
                    statusContainer.removeClass('fsim-status-success');
                    statusContainer.addClass('fsim-status-error');

                    statusTab.removeClass('fsim-status-success');
                    statusTab.addClass('fsim-status-error');

                    // swap start and stop functions
                    startstopButton.removeClass('stop-slave');
                    startstopButton.addClass('start-slave');

                    // set tooltip to Start
                    startstopButton.prop('text', 'START');

                    break;
            }
        } else if (status.payload['program_status'] != null) {
            // handle program status updates

            let statusContainer = $('#programStatusContainer_' + status.payload['pid']);
            let startstopButton = $('#programStartStop_' + status.payload['pid']);

            switch (status.payload['program_status']) {
                case 'started':
                    statusContainer.removeClass(function (index, className) {
                        return (className.match(/(^|\s)fsim-status-\S+/g) || []).join(' ');
                    });

                    statusContainer.addClass('fsim-status-warn');

                    startstopButton.data('is-running', true);
                    startstopButton.prop('text', 'STOP');
                    break;
                case 'finished':
                    statusContainer.removeClass(function (index, className) {
                        return (className.match(/(^|\s)fsim-status-\S+/g) || []).join(' ');
                    });

                    if (status.payload['code'] !== 0) {
                        statusContainer.addClass('fsim-status-error');
                    } else {
                        statusContainer.addClass('fsim-status-success');
                    }

                    startstopButton.data('is-running', false);
                    startstopButton.prop('text', 'START');
                    break;
            }
        } else if (status.payload['message'] != null) {
            $.notify({
                message: status.payload['message']
            });
        } else {
            $.notify({
                type: 'warning',
                message: 'Received unknown response from server'
            });
        }
    } else {
        $.notify({
            type: 'danger',
            message: status.payload
        });
    }
};

// Call onopen directly if socket is already open
if (socket.readyState === WebSocket.OPEN) socket.onopen();
