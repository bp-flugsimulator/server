/* eslint-env browser*/
/* global $, getCookie, Status, fsimWebsocket, notify*/

var socketEventHandler = {
    scriptWaitForSlaves(payload) {
        console.log("wait");
        notify('Waiting for client ', 'Waiting for all clients to connect.', 'info');
    },
    scriptNextStep(payload) {
        console.log("next");

        notify('Stage ' + payload.last_index + ' done', 'All programs for index ' + payload.index + ' have been started. The next stage will take ' + payload.start_time + ' seconds.', 'info');
    },
    scriptSuccess(payload) {
        console.log("success");
        notify('Success', 'The script has been successfully started.', 'success');
    },
    scriptError(payload) {
        console.log("error");
        notify('Error', 'There was an error while running the script.', 'danger');
    },
};

var socket = fsimWebsocket(socketEventHandler);

$(document).ready(function () {
    $('.script-action-run').click(function (event) {
        event.preventDefault();
        let id = $(this).attr('data-script-id');

        $.ajax({
            type: 'GET',
            url: '/api/script/' + id + '/run',
            beforeSend(xhr) {
                xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
            },
            converters: {
                'text json': Status.from_json
            },
            success(status) {
                if (status.is_err()) {
                    notify('Error while starting', 'Could not start script. (' + JSON.stringify(status.payload) + ')', 'danger');
                }
            },
            error(xhr, errorString, errorCode) {
                notify('Error while transport', errorCode, 'danger');
            }
        });
    });
});
