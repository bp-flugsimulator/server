/* eslint-env browser*/
/* eslint no-use-before-define: ["error", { "functions": false }] */
/* global $, fsimWebsocket, notify, basicRequest */
/* exported socket */

const socketEventHandler = {
    scriptWaitForSlaves(payload) {
        $('#waitSlavesIcon').attr('data-state', 'waiting');
        $('#runInit' + payload.script_id).attr('data-state', 'done');
        $('#clientCollapse').addClass('show');
    },
    scriptNextStep(payload) {
        if (payload.last_index === -1) {
            $('#waitSlavesIcon').attr('data-state', 'done');
            $('#clientCollapse').removeClass('show');
        } else {
            $('#runStage' + payload.last_index).attr('data-state', 'done');
            $('#stageCollapse' + payload.last_index).removeClass('show');
        }

        $('#runStage' + payload.index).attr('data-state', 'waiting');
        $('#stageCollapse' + payload.index).addClass('show');
    },
    scriptSuccess(payload) {
        $('#scriptTabContent' + payload.script_id + ' [data-state="waiting"]').attr('data-state', 'done');
        $('#runDone' + payload.script_id).attr('data-state', 'done');
        $('#scriptTabNav' + payload.script_id + ' .fsim-script-status-icon').attr('data-state', 'done');
    },
    scriptError(payload) {
        $('#scriptTabContent' + payload.script_id + ' [data-state="waiting"]').attr('data-state', 'error');
        $('#scriptTabNav' + payload.script_id + ' .fsim-script-status-icon').attr('data-state', 'error');
        notify('Error', 'There was an error while running the script. (' + payload.error_code + ')', 'danger');
    },
    slaveConnect(payload) {
        let statusTab = $('#slaveTab' + payload.sid);
        statusTab.attr('data-state', 'success');
    },
    slaveDisconnect(payload) {
        let statusTab = $('#slaveTab' + payload.sid);
        statusTab.attr('data-state', 'unknown');
    },
    programStarted(payload) {
        let statusContainer = $('#programStatusContainer_' + payload.pid);
        statusContainer.attr('data-state', 'warning');
    },
    programStopped(payload) {
        let statusContainer = $('#programStatusContainer_' + payload.pid);

        let error = false;

        if (payload.code !== 0 && payload.code !== '0') {
            error = true;
            statusContainer.attr('data-state', 'error');
        } else {
            statusContainer.attr('data-state', 'success');
        }
    },
    filesystemMoved(payload) {
        let statusContainer = $('#filesystemStatusContainer_' + payload.fid);
        statusContainer.attr('data-state', 'moved');
    },
    filesystemRestored(payload) {
        let statusContainer = $('#filesystemStatusContainer_' + payload.fid);
        statusContainer.attr('data-state', 'restored');
    },
    filesystemError(payload) {
        let statusContainer = $('#filesystemStatusContainer_' + payload.fid);
        statusContainer.attr('data-state', 'error');
    },
};

const socket = fsimWebsocket(socketEventHandler);

$(document).ready(function () {
    $('.script-action-stop').click(function (event) {
        //let id = $(this).attr('data-script-id'); Not important
        basicRequest({
            type: 'POST',
            url: '/api/script/stop',
            action: 'stop script',
            onSuccess() {
                window.location.reload();
            },
        });
    });
});
