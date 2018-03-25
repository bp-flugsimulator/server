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
        let timestamp = $('#program_' + payload.pid + '_start_time');
        let now = Math.round((new Date()).getTime() / 1000);
        timestamp.removeAttr('data-timestamp');
        timestamp.attr('data-timestamp', now);
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

/**
 * Updates the timestamps of every Program that has a start_time.
 */
function refreshTimestamps(){
    let now = Math.round((new Date()).getTime() / 1000);

    $('.stage').each(function (_) {
        let start_time = 0;
        let timestamp = 0;
        let elapsed_time = 0;

        $(this).children().find('.timestamp').each(function () {
            let child_start_time = $(this).attr('data-start-time');
            let child_timestamp = $(this).attr('data-timestamp');
            let child_elapsed_time = now - child_timestamp;
            if(child_start_time - child_elapsed_time > start_time - elapsed_time){
                start_time = child_start_time;
                timestamp = child_timestamp;
                elapsed_time = child_elapsed_time;
            }
        });

        if((start_time !== 0 || elapsed_time !== 0) && $(this).attr('data-state') === 'waiting') {
            $(this).children('.stage-timestamp').text('(' + elapsed_time + '/' + start_time + ' s)');
        } else {
            $(this).children('.stage-timestamp').text('');
        }
    });

    $('.timestamp').each(function(_) {
        let start_time = $(this).attr('data-start-time');
        let timestamp = $(this).attr('data-timestamp');
        let elapsed_time = now - timestamp;

        if (start_time === '0' || start_time === '-1'){
            return;
        }
        let text = '(';

        if(timestamp === '0'){
            text += '0';
        } else if(elapsed_time < start_time){
            text += elapsed_time;
        } else {
            text += start_time;
        }

        $(this).text(text + '/' + start_time + ' s)');
    });
}

$(document).ready(function () {
    window.setInterval(function(){refreshTimestamps()}, 500);

    $('.script-action-stop').click(function (event) {
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
