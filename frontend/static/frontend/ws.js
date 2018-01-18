/* eslint-env browser*/
/* global $, Status, swapText, styleSlaveByStatus */
/*eslint no-console: ["error", { allow: ["log"] }] */

function changeStartStopText(element, text) {
    element.children('.button-status-display').each(function (idx, val) {
        $(val).text(text);
    });
}

var socket = new WebSocket('ws://' + window.location.host + '/notifications');

var socketEventHandler = {
    slaveConnect(payload) {
        let statusContainer = $('#slaveStatusContainer_' + payload.sid);
        let statusTab = $('#slaveTab' + payload.sid);
        let startstopButton = $('#slaveStartStop_' + payload.sid);

        statusContainer.attr('data-state', 'success');
        statusTab.attr('data-state', 'success');

        // Use Python notation !!!
        startstopButton.attr('data-is-running', 'True');
        changeStartStopText(startstopButton, 'STOP');

        // set tooltip to Stop
        startstopButton.children('[data-text-swap]').each(function (idx, val) {
            swapText($(val));
        });
    },
    slaveDisconnect(payload) {
        let statusContainer = $('#slaveStatusContainer_' + payload.sid);
        let statusTab = $('#slaveTab' + payload.sid);
        let startstopButton = $('#slaveStartStop_' + payload.sid);

        statusContainer.attr('data-state', 'unkown');
        statusTab.attr('data-state', 'unkown');

        $('#slavesObjectsProgramsContent' + payload.sid)
            .find('.fsim-box[data-state]')
            .each(function (idx, val) {
                $(val).attr('data-state', 'unkown');
            });

        // Use Python notation !!!
        startstopButton.attr('data-is-running', 'False');
        changeStartStopText(startstopButton, 'START');

        // set tooltip to Start
        startstopButton.children('[data-text-swap]').each(function (idx, val) {
            swapText($(val));
        });
    },
    programStarted(payload) {
        let statusContainer = $('#programStatusContainer_' + payload.pid);
        let startstopButton = $('#programStartStop_' + payload.pid);
        let cardButton = $('#programCardButton_' + payload.pid);

        statusContainer.attr('data-state', 'warning');
        cardButton.prop('disabled', true);

        // Use Python notation !!!
        startstopButton.attr('data-is-running', 'True');
        changeStartStopText(startstopButton, 'STOP');

        let sid = null;

        statusContainer.find('button[data-slave-id]').each(function (idx, val) {
            sid = $(val).data('slave-id');
            return false;
        });

        styleSlaveByStatus(sid);

        startstopButton.children('[data-text-swap]').each(function (idx, val) {
            swapText($(val));
        });
    },
    programStopped(payload) {
        let statusContainer = $('#programStatusContainer_' + payload.pid);
        let startstopButton = $('#programStartStop_' + payload.pid);
        let cardButton = $('#programCardButton_' + payload.pid);
        let cardBox = $('#programCard_' + payload.pid);

        if (payload.code !== 0) {
            statusContainer.attr('data-state', 'error');

            cardButton.prop('disabled', false);
            cardBox.text(payload.code);
        } else {
            statusContainer.attr('data-state', 'success');
        }

        // Use Python notation !!!
        startstopButton.attr('data-is-running', 'False');
        changeStartStopText(startstopButton, 'START');

        let sid = null;

        statusContainer.find('button[data-slave-id]').each(function (idx, val) {
            sid = $(val).data('slave-id');
            return false;
        });

        styleSlaveByStatus(sid);

        startstopButton.children('[data-text-swap]').each(function (idx, val) {
            swapText($(val));
        });
    },
};

socket.onmessage = function (data) {
    let status = Status.from_json(data.data);
    console.log(status);

    if (status.is_ok()) {
        if (status.payload['slave_status'] != null) {
            // handle slave status updates
            switch (status.payload['slave_status']) {
                case 'connected':
                    socketEventHandler.slaveConnect(status.payload);
                    break;
                case 'disconnected':
                    socketEventHandler.slaveDisconnect(status.payload);
                    break;
            }
        } else if (status.payload['program_status'] != null) {
            // handle program status updates
            switch (status.payload['program_status']) {
                case 'started':
                    socketEventHandler.programStarted(status.payload);
                    break;
                case 'finished':
                    socketEventHandler.programStopped(status.payload);
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
