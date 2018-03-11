/* eslint-env browser*/
/* eslint no-use-before-define: ["error", { "functions": false }] */
/* global $, fsimWebsocket, notify, basicRequest */
/* exported socket */

var socketEventHandler = {
    scriptWaitForSlaves(payload) {
        $('#scriptTabNav' + payload.script_id + ' .fsim-script-status-icon').attr('data-state', 'waiting');

        $('#runInit' + payload.script_id).attr('data-state', 'done');
        $('#runWaitSlaves' + payload.script_id).attr('data-state', 'waiting');
        // notify('Waiting for client ', 'Waiting for all clients to connect.', 'info');
    },
    scriptNextStep(payload) {
        if (payload.last_index === -1) {
            $('#runWaitSlaves' + payload.script_id).attr('data-state', 'done');
        } else {
            $('#runStage' + payload.script_id + '_' + payload.last_index).attr('data-state', 'done');
        }

        $('#runStage' + payload.script_id + '_' + payload.index).attr('data-state', 'waiting');
        // notify('Stage ' + payload.last_index + ' done', 'All programs for index ' + payload.index + ' have been started. The next stage will take ' + payload.start_time + ' seconds.', 'info');
    },
    scriptSuccess(payload) {
        $('#scriptTabContent' + payload.script_id + ' [data-state="waiting"]').attr('data-state', 'done');
        $('#runDone' + payload.script_id).attr('data-state', 'done');
        $('#scriptTabNav' + payload.script_id + ' .fsim-script-status-icon').attr('data-state', 'done');
        // notify('Success', 'The script has been successfully started.', 'success');
    },
    scriptError(payload) {
        $('#scriptTabContent' + payload.script_id + ' [data-state="waiting"]').attr('data-state', 'error');
        $('#scriptTabNav' + payload.script_id + ' .fsim-script-status-icon').attr('data-state', 'error');
        notify('Error', 'There was an error while running the script. (' + payload.error_code + ')', 'danger');
    },
};

var socket = fsimWebsocket(socketEventHandler);

$(document).ready(function () {
    $('.script-action-run').click(function (event) {
        event.preventDefault();
        let id = $(this).attr('data-script-id');
        $('#scriptTabContent' + id + ' [data-state]').attr('data-state', 'none');

        basicRequest({
            type: 'POST',
            url: '/api/script/' + id + '/run',
            action: 'start script',
            onError(payload) {
                notify('Error while starting', 'Could not start script. (' + JSON.stringify(payload) + ')', 'danger');
            }
        });
    });
});
