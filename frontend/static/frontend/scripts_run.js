/* eslint-env browser*/
/* global $, getCookie, Status, fsimWebsocket, notify*/

var socketEventHandler = {
    scriptWaitForSlaves(payload) {
        $('.fsim-progressbar-step').each(function (idx, val) {
            $(val).attr('data-state', 'wait');
        });

        console.log("wait");
        notify('Waiting for client ', 'Waiting for all clients to connect.', 'info');
    },
    scriptNextStep(payload) {
        let mode = '';

        if (payload.start_time <= 0) {
            mode = 'wait';
        } else {
            mode = 'timer';
        }

        $('.fsim-progressbar-step').each(function (idx, val) {
            $(val).attr('data-state', mode);
            let last = $(val).children('.fsim-progressbar-name').last().val();
            $(val).children('.fsim-progressbar-name').first().val(last);
            $(val).children('.fsim-progressbar-name').last().val('Step: ' + payload.index);
        });

        // $(".fsim-progressbar-step").after().animate({
        //     width: "100%"
        // }, payload.start_time * 1000);

        console.log("next");
        notify('Stage done', 'All programs for index {} have been started. The next stage will take {} seconds.'.format(payload.index, payload.start_time), 'info');
    },
    scriptSuccess(payload) {
        $('.fsim-progressbar-step').each(function (idx, val) {
            $(val).attr('data-state', 'success');
            $(val).css('width', "100%");
        });

        console.log("success");

        notify('Success', 'The script has been successfully started.', 'success');
    },
    scriptError(payload) {
        $('.fsim-progressbar-step').each(function (idx, val) {
            $(val).attr('data-state', 'error');
            $(val).css('width', "100%");
        });

        console.log("error");
        notify('Error', 'There was an error while running the script.', 'danger');
    },
};

var socket = fsimWebsocket(socketEventHandler);

$(document).ready(function () {
    $('#scriptRun').click(function (event) {
        event.preventDefault();
        let id = $('#scriptSelect :selected').val();

        if (id == null) {
            notify('No script selected.', 'You have to select a script first', 'danger');
        } else {
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
        }
    });
});
