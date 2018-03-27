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
        statusContainer.attr('data-state', 'running');
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
        let startTime = 0;
        let timestamp = 0;
        let elapsedTime = 0;

        $(this).children().find('.timestamp').each(function () {
            let childStartTime = $(this).attr('data-start-time');
            let childTimestamp = $(this).attr('data-timestamp');
            let childElapsedTime = now - childTimestamp;
            if(childStartTime - childElapsedTime > startTime - elapsedTime){
                startTime = childStartTime;
                timestamp = childTimestamp;
                elapsedTime = childElapsedTime;
            }
        });

        if((startTime !== 0 || elapsedTime !== 0) && $(this).attr('data-state') === 'waiting') {
            $(this).children('.stage-timestamp').text('(' + elapsedTime + '/' + startTime + ' s)');
        } else {
            $(this).children('.stage-timestamp').text('');
        }
    });

    $('.timestamp').each(function(_) {
        let startTime = $(this).attr('data-start-time');
        let timestamp = $(this).attr('data-timestamp');
        let elapsedTime = now - timestamp;

        if (startTime === '0' || startTime === '-1'){
            return;
        }
        let text = '(';

        if(timestamp === '0'){
            text += '0';
        } else if(elapsedTime < startTime){
            text += elapsedTime;
        } else {
            text += startTime;
        }

        $(this).text(text + '/' + startTime + ' s)');
    });
}

$(document).ready(function () {
    window.setInterval(function(){refreshTimestamps();}, 500);

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

    if ($('.countdown-value[data-value][data-script]').first() !== null) {
        var countdownCurrent = 30;
        var interval = setInterval(function() {
            countdownCurrent -= 1;

            $('.countdown-value[data-value][data-script]').each(function(idx, val) {
                val.setAttribute('data-value', countdownCurrent);
            });

            let script = $('.countdown-value[data-value][data-script]').first().attr('data-script');

            if (countdownCurrent === 0) {
                clearInterval(interval);
                basicRequest({
                    type: 'POST',
                    url: '/api/script/' + script + '/run',
                    action: 'start script',
                    onSuccess: function() {
                        window.location.href = '/scripts/run';
                    },
                    onError: function() {
                        window.location.href = '/scripts/run';
                    }
                });
            }
        }, 1000);

        $('.countdown-abort').on('click', function() {
            clearInterval(interval);
        });
    }
});
