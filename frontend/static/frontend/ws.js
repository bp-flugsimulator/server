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
                    statusContainer.attr('data-state', 'success');
                    statusTab.attr('data-state', 'success');

                    // swap start and stop functions
                    startstopButton.removeClass('start-slave');
                    startstopButton.addClass('stop-slave');

                    // set tooltip to Stop
                    startstopButton.text('STOP');

                    break;
                case 'disconnected':
                    // swap status
                    statusContainer.attr('data-state', 'unkown');
                    statusTab.attr('data-state', 'unkown');

                    // swap start and stop functions
                    startstopButton.removeClass('stop-slave');
                    startstopButton.addClass('start-slave');

                    // set tooltip to Start
                    startstopButton.text('START');

                    break;
            }
        } else if (status.payload['program_status'] != null) {
            // handle program status updates
            let statusContainer = $('#programStatusContainer_' + status.payload['pid']);
            let startstopButton = $('#programStartStop_' + status.payload['pid']);
            let statusIcon = $('#programStatusIcon_' + status.payload['pid']);
            let cardButton = $('#programCardButton_' + status.payload['pid']);
            let cardBox = $('#programCard_' + status.payload['pid']);

            switch (status.payload['program_status']) {
                case 'started':
                    statusIcon.removeClass(function (index, className) {
                        return (className.match(/(^|\s)mdi-\S+/g) || []).join(' ');
                    });

                    statusContainer.attr('data-state', 'warning');
                    console.log(statusContainer);

                    statusIcon.addClass('mdi-cached');
                    statusIcon.addClass('mdi-spin');

                    cardButton.prop('disabled', true);

                    startstopButton.attr('data-is-running', true);
                    startstopButton.text('STOP');
                    break;
                case 'finished':
                    statusIcon.removeClass(function (index, className) {
                        return (className.match(/(^|\s)mdi-\S+/g) || []).join(' ');
                    });

                    if (status.payload['code'] !== 0) {
                        statusContainer.attr('data-state', 'error');
                        statusIcon.addClass('mdi-error-outline')
                        cardButton.prop('disabled', false);
                        cardBox.text(status.payload['code']);
                    } else {
                        statusContainer.attr('data-state', 'success');
                        statusIcon.addClass('mdi-check')
                    }

                    startstopButton.attr('data-is-running', false);
                    startstopButton.text('START');
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
if (socket.readyState === WebSocket.OPEN) {
    socket.onopen();
}
