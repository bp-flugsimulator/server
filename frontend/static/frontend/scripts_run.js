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
        let statusContainer = $('#slaveStatusContainer_' + payload.sid);
        let statusTab = $('#slaveTab' + payload.sid);
        let startstopButton = $('#slaveStartStop_' + payload.sid);

        statusContainer.attr('data-state', 'success');
        statusTab.attr('data-state', 'success');

        // Use Python notation !!!
        startstopButton.attr('data-is-running', 'True');
        changeStatusDisplayText(startstopButton, 'SWITCH OFF');

        // set tooltip to Stop
        startstopButton.children('[data-text-swap]').each(function (idx, val) {
            swapText($(val));
        });
    },
    slaveDisconnect(payload) {
        let statusContainer = $('#slaveStatusContainer_' + payload.sid);
        let statusTab = $('#slaveTab' + payload.sid);
        let startstopButton = $('#slaveStartStop_' + payload.sid);

        statusContainer.attr('data-state', 'unknown');
        statusTab.attr('data-state', 'unknown');

        $('#slavesObjectsProgramsContent' + payload.sid)
            .find('.fsim-box[data-state]')
            .each(function (idx, val) {
                $(val).attr('data-state', 'unknown');
            });

        // Use Python notation !!!
        startstopButton.attr('data-is-running', 'False');
        changeStatusDisplayText(startstopButton, 'SWITCH ON');

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
        cardButton.prop('disabled', false);

        // Use Python notation !!!
        startstopButton.attr('data-is-running', 'True');
        changeStatusDisplayText(startstopButton, 'STOP');

        let sid = null;

        statusContainer.find('button[data-slave-id]').each(function (idx, val) {
            sid = $(val).data('slave-id');
            return false;
        });

        styleSlaveByStatus(sid, false, false, true, true);

        startstopButton.children('[data-text-swap]').each(function (idx, val) {
            swapText($(val));
        });
    },
    programStopped(payload) {
        let statusContainer = $('#programStatusContainer_' + payload.pid);
        let startstopButton = $('#programStartStop_' + payload.pid);

        let cardButton = $('#programCardButton_' + payload.pid);
        cardButton.prop('disabled', false);

        let error = false;

        if (payload.code !== 0 && payload.code !== '0') {
            error = true;
            statusContainer.attr('data-state', 'error');
        } else {
            statusContainer.attr('data-state', 'success');
        }

        // Use Python notation !!!
        startstopButton.attr('data-is-running', 'False');
        changeStatusDisplayText(startstopButton, 'START');

        let sid = null;

        statusContainer.find('button[data-slave-id]').each(function (idx, val) {
            sid = $(val).data('slave-id');
            return false;
        });

        styleSlaveByStatus(sid, error, error, true, false);

        startstopButton.children('[data-text-swap]').each(function (idx, val) {
            swapText($(val));
        });
    },
    filesystemMoved(payload) {
        let statusContainer = $('#filesystemStatusContainer_' + payload.fid);
        let moveRestoreButton = $('#filesystemMoveRestore_' + payload.fid);
        let cardButton = $('#filesystemCardButton_' + payload.fid);

        statusContainer.attr('data-state', 'moved');
        cardButton.prop('disabled', true);

        // Use Python notation !!!
        moveRestoreButton.attr('data-is-moved', 'True');
        changeStatusDisplayText(moveRestoreButton, 'RESTORE');
    },
    filesystemRestored(payload) {
        let statusContainer = $('#filesystemStatusContainer_' + payload.fid);
        let moveRestoreButton = $('#filesystemMoveRestore_' + payload.fid);
        let cardButton = $('#filesystemCardButton_' + payload.fid);

        statusContainer.attr('data-state', 'restored');
        cardButton.prop('disabled', true);

        // Use Python notation !!!
        moveRestoreButton.attr('data-is-moved', 'False');
        changeStatusDisplayText(moveRestoreButton, 'MOVE');
    },
    filesystemError(payload) {
        let statusContainer = $('#filesystemStatusContainer_' + payload.fid);
        let cardButton = $('#filesystemCardButton_' + payload.fid);
        let cardBox = $('#filesystemCard_' + payload.fid);

        statusContainer.attr('data-state', 'error');
        cardButton.prop('disabled', false);
        cardBox.text(payload.error_code);

        let sid = null;

        statusContainer.find('button[data-slave-id]').each(function (idx, val) {
            sid = $(val).data('slave-id');
            return false;
        });

        styleSlaveByStatus(sid, true, true, false, false);
    },
};

var socket = fsimWebsocket(socketEventHandler);

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
