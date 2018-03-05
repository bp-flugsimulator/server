/* eslint-env browser*/
/* eslint no-use-before-define: ["error", { "functions": false }] */
/* global $, getCookie, modalDeleteAction, handleFormStatus, clearErrorMessages, Status,
 fsimWebsocket, notify, swapText, styleSlaveByStatus, basicRequest */

/**
 * Sets the given text for all '.button-status-display' in a container.
 *
 * @param {HTMlElement} element A container which holds a element with '.button-status-display'
 * @param {String} text A text which will be set for all '.button-status-display'
 */
function changeStatusDisplayText(element, text) {
    element.children('.button-status-display').each(function (idx, val) {
        $(val).text(text);
    });
}

/**
 * Creates a function which handles from submits.
 *
 * @param {String} id Form identifier without '#'
 */
function onFormSubmit(id) {
    return function (event) {
        //Stop form from submitting normally
        event.preventDefault();

	//remove the unload-Hook
	window.unloadPrompt = false;

        //send request to given url and with given method
        //data field contains information about the slave
        $.ajax({
            type: $(this).attr('method'),
            url: $(this).attr('action'),
            data: $(this).serialize(),
            converters: {
                'text json': Status.from_json
            },
            beforeSend(xhr) {
                xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
            },
            success(status) {
                handleFormStatus($('#' + id), status);
            },
            error(xhr, errorString, errorCode) {
                notify('Could deliver', 'Could not send data to server.' + errorCode + ')', 'danger');
            }
        });
    };
}

/**
 * Restores the active tab for a slave container by clicking on the tab.
 *
 * @param {Integer} slaveId
 */
function restoreSlaveInnerTab(slaveId) {
    let tabStatus = localStorage.getItem('tab-status');

    if (tabStatus !== null) {
        if (tabStatus === 'program') {
            $('#slavesObjectsPrograms' + slaveId).click();
        }
        else if (tabStatus === 'filesystem') {
            $('#slavesObjectsFiles' + slaveId).click();
        }
    }
}

function handleLogging(id, method, async = true) {
    $.ajax({
        type: 'GET',
        url: '/api/program/' + id + '/log/' + method,
        async: async,
        beforeSend(xhr) {
            xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
        },
        converters: {
            'text json': Status.from_json
        },
        success(status) {
            if (status.is_err()) {
                notify('Error while handeling a log', 'Could not handle log. (' + JSON.stringify(status.payload) + ')', 'danger');
            }
        },
        error(xhr, errorString, errorCode) {
            notify('Could deliver', 'Could not deliver request `GET` to server.' + errorCode + ')', 'danger');
        }
    });
}

let terminals = {};

const socketEventHandler = {
    slaveConnect(payload) {
        let statusContainer = $('#slaveStatusContainer_' + payload.sid);
        let statusTab = $('#slaveTab' + payload.sid);
        let startstopButton = $('#slaveStartStop_' + payload.sid);

        statusContainer.attr('data-state', 'success');
        statusTab.attr('data-state', 'success');

        // Use Python notation !!!
        startstopButton.attr('data-is-running', 'True');
        changeStatusDisplayText(startstopButton, 'STOP');

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
        changeStatusDisplayText(startstopButton, 'START');

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

        styleSlaveByStatus(sid);

        startstopButton.children('[data-text-swap]').each(function (idx, val) {
            swapText($(val));
        });
    },
    programStopped(payload) {
        let statusContainer = $('#programStatusContainer_' + payload.pid);
        let startstopButton = $('#programStartStop_' + payload.pid);

        let cardButton = $('#programCardButton_' + payload.pid);
        cardButton.prop('disabled', false);

        if (payload.code !== 0 && payload.code !== '0') {
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

        styleSlaveByStatus(sid);

        startstopButton.children('[data-text-swap]').each(function (idx, val) {
            swapText($(val));
        });
    },
    programUpdateLog(payload) {
        let pid = payload.pid;
        if (terminals[pid] == null) {
            terminals[pid] = new AnsiTerm(pid, 80);
        }

        terminals[pid].feed(payload.log);
        $('#waitingText_' + pid).empty();
        $('#programLog_' + pid).data('has-log', true);
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

        let sid = null;

        statusContainer.find('button[data-slave-id]').each(function (idx, val) {
            sid = $(val).data('slave-id');
            return false;
        });

        styleSlaveByStatus(sid);
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

        let sid = null;

        statusContainer.find('button[data-slave-id]').each(function (idx, val) {
            sid = $(val).data('slave-id');
            return false;
        });

        styleSlaveByStatus(sid);
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

        styleSlaveByStatus(sid);
    },
};

/**
 * Init Websocket
 */
fsimWebsocket(socketEventHandler);

$(document).ready(function () {
    // Restores the last clicked slave
    (function () {
        let href = localStorage.getItem('status');
        if (href !== null) {
            let iter = $('.slave-tab-link').filter(function (idx, val) {
                return val.hasAttribute('href') && val.getAttribute('href') === href;
            });

            iter.click();

            let slaveId = iter.attr('data-slave-id');
            restoreSlaveInnerTab(slaveId);
        }
    }());

    // Set color of the current selected.
    $('.slave-tab-link.active').parent('li').css('background-color', '#dbdbdc');

    // Changes the color of the clicked slave, if it was not clicked before.
    $('.slave-tab-link').click(function () {
        if (!$(this).hasClass('active')) {
            // Remove color from the old tabs
            $('.slave-tab-link').each(function (idx, val) {
                $(val).parent('li').css('background-color', 'transparent');
            });

            // Save Class when opening for every Slave
            localStorage.setItem('status', $(this).attr('href'));

            // Change the color of the current tab
            $(this).parent('li').css('background-color', '#dbdbdc');
        }
    });

    $('.slave-filesystem-tab').click(function () {
        localStorage.setItem('tab-status', 'filesystem');
    });

    $('.slave-program-tab').click(function () {
        localStorage.setItem('tab-status', 'program');
    });


    $('.program-action-handle-logging').click(function () {
        let pid = $(this).data('program-id');
        let logBox = $('#programLog_' + pid);

        if (!$(this).data('enabled')) {
            let waitingText = $('<span/>',{
                id: 'waitingText_' + pid,
                text:'Processing the log from the client.\n'
            });
            logBox.append(waitingText);
            $(this).data('enabled', true);
            handleLogging(pid, 'enable');
        } else {
            handleLogging(pid, 'disable');
            $(this).data('enabled', false);
            terminals[pid].clear();
        }
    });


    $('.program-action-start-stop').click(function () {
        let apiRequest = function (url, type) {
            $.ajax({
                type,
                url,
                beforeSend(xhr) {
                    xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
                },
                converters: {
                    'text json': Status.from_json
                },
                success(status) {
                    if (status.is_err()) {
                        notify('Error while starting program', 'Could not start program. (' + JSON.stringify(status.payload) + ')', 'danger');
                    }
                },
                error(xhr, errorString, errorCode) {
                    notify('Could deliver', 'Could not deliver request `' + type + '` to server.' + errorCode + ')', 'danger');
                }
            });
        };

        let id = $(this).data('program-id');

        let cardButton = $('#programCardButton_' + id);
        cardButton.prop('disabled', false);

        if ($(this).attr('data-is-running') === 'True') {
            apiRequest('/api/program/' + id + '/stop', 'GET');
        } else if ($(this).attr('data-is-running') === 'False') {
		apiRequest('/api/program/' + id + '/start', 'GET');
        }
    });

    function prepareDeleteModal(show, id, message) {
        //changing button visibility and message of the delete modal
        let deleteWarning = $('#deleteWarning');
        deleteWarning.children().find('#deleteProgramModalButton').hide();
        deleteWarning.children().find('#deleteSlaveModalButton').hide();
        deleteWarning.children().find('#deleteFilesystemModalButton').hide();

        deleteWarning.children().find('#delete' + show + 'ModalButton').show();

        deleteWarning.children().find('.modal-body').empty(message);
        deleteWarning.children().find('.modal-body').append(message);


        //adding id to modal and set it visible
        deleteWarning.data('sqlId', id);
        deleteWarning.modal('toggle');
    }

    //opens the programModal to add a new program
    $('.program-action-add').click(function () {
        let programModal = $('#programModal');
        programModal.children().find('.modal-title').text('Add Program');

        //modify the form for the submit button
        let programForm = programModal.children().find('#programForm');
        programForm.attr('action', '/api/programs');
        programForm.attr('method', 'POST');
        programForm.children().find('.submit-btn').text('Add');

        //clear input fields

        programForm.find('[name="name"]').val('');
        programForm.find('[name="path"]').val('');
        programForm.find('[name="arguments"]').val('');

        //clear error messages
        clearErrorMessages(programForm);

        //find slave id and store it in the form
        let slaveId = $(this).data('slave-id');
        programForm.find('[name="slave"]').val(slaveId);
        programModal.modal('toggle');
    });

    //opens the programModal to modify a program
    $('.program-action-modify').click(function () {
        let programModal = $('#programModal');
        let programForm = programModal.children().find('#programForm');

        //get info of program
        let id = $(this).data('program-id');
        let name = $(this).data('program-name');
        let path = $(this).data('program-path');
        let args = $(this).data('program-arguments');
        let startTime = $(this).data('program-start-time');

        //modify the form for the submit button
        programModal.children().find('.modal-title').text('Edit Program');
        programForm.attr('action', '/api/program/' + id);
        programForm.attr('method', 'PUT');
        programForm.children().find('.submit-btn').text('Edit');

        //clear input fields
        programForm.find('[name="name"]').val(name);
        programForm.find('[name="path"]').val(path);
        programForm.find('[name="arguments"]').val(args);
        programForm.find('[name="start_time"]').val(startTime);

        //clear error messages
        clearErrorMessages(programForm);

        //find slave id and store it in the form
        let slaveId = $(this).data('slave-id');
        programForm.find('[name="slave"]').val(slaveId);

        //find slave id and store it in the form
        programModal.modal('toggle');
    });

    $('#deleteProgramModalButton').click(function () {
        modalDeleteAction($('#programForm'), 'program');
    });

    $('.program-action-delete').click(function () {
        //get id and name of the program and create deletion message
        let id = $(this).data('program-id');
        let name = $(this).data('program-name');
        let message = '<a>Are you sure you want to remove program </a><b>' + name + '</b>?</a>';

        prepareDeleteModal('Program', id, message);
    });

    // programForm Handler
    $('#programForm').submit(onFormSubmit('programForm'));

    //opens the fileModal to add a new program
    $('.filesystem-action-add').click(function () {
        let filesystemModal = $('#filesystemModal');
        filesystemModal.children().find('.modal-title').text('Add filesystem');

        //modify the form for the submit button
        let filesystemForm = filesystemModal.children().find('#filesystemForm');
        filesystemForm.attr('action', '/api/filesystems');
        filesystemForm.attr('method', 'POST');
        filesystemForm.children().find('.submit-btn').text('Add');

        //clear input fields
        filesystemForm.find('[name="name"]').val('');
        filesystemForm.find('[name="source_path"]').val('');
        filesystemForm.find('[name="destination_path"]').val('');

        //clear error messages
        clearErrorMessages(filesystemForm);

        //find slave id and store it in the form
        let slaveId = $(this).data('slave-id');
        filesystemForm.find('[name="slave"]').val(slaveId);
        filesystemModal.modal('toggle');
    });

    $('.filesystem-action-modify').click(function () {
        let filesystemModal = $('#filesystemModal');
        let filesystemForm = filesystemModal.children().find('#filesystemForm');

        //get info of the filesystem
        let id = $(this).data('filesystem-id');
        let name = $(this).data('filesystem-name');
        let sourcePath = $(this).data('filesystem-source_path');
        let destinationPath = $(this).data('filesystem-destination_path');
		
        //modify the form for the submit button
        filesystemModal.children().find('.modal-title').text('Edit Filesystem');
        filesystemForm.attr('action', '/api/filesystem/' + id);
        filesystemForm.attr('method', 'PUT');
        filesystemForm.children().find('.submit-btn').text('Edit');

        //set values into input fields
        filesystemForm.find('[name="name"]').val(name);
        filesystemForm.find('[name="source_path"]').val(sourcePath);
        filesystemForm.find('[name="destination_path"]').val(destinationPath);

        //clear error messages
        clearErrorMessages(filesystemForm);

        //find slave id and store it in the form
        let slaveId = $(this).data('slave-id');
        filesystemForm.find('[name="slave"]').val(slaveId);

        //find slave id and store it in the form
        filesystemModal.modal('toggle');
    });

    $('.filesystem-action-delete').click(function () {
        //get id and name of the program and create deletion message
        let id = $(this).data('filesystem-id');
        let name = $(this).data('filesystem-name');
        let message = '<a>Are you sure you want to remove filesystem </a><b>' + name + '</b>?</a>';

        prepareDeleteModal('Filesystem', id, message);
    });

    $('.filesystem-action-move').click(function () {
        let id = $(this).data('filesystem-id');

        if ($(this).attr('data-is-moved') === 'True') {
            basicRequest('/api/filesystem/' + id + '/restore', 'GET', 'restore entry in filesystem');
        } else if ($(this).attr('data-is-moved') === 'False') {
            basicRequest('/api/filesystem/' + id + '/move', 'GET', 'move entry in filesystem');
        }
    });

    $('#deleteFilesystemModalButton').click(function () {
        modalDeleteAction($('#filesystemForm'), 'filesystem');
    });

    // filesystemForm Handler
    $('#filesystemForm').submit(onFormSubmit('filesystemForm'));

    $('.slave-action-start-stop').click(function () {
        if ($(this).attr('data-is-running') === 'True') {
            let id = $(this).data('slave-id');
            let el = $(this);

            $.ajax({
                type: 'GET',
                url: '/api/slave/' + id + '/shutdown',
                beforeSend(xhr) {
                    xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
                },
                converters: {
                    'text json': Status.from_json
                },
                success(status) {
                    if (status.is_ok()) {
                        el.addClass('animated pulse');
                        el.one('webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend', function () {
                            el.removeClass('animated pulse');
                        });
                    } else {
                        notify('Could not stop client', 'The client could not be stopped. (' + JSON.stringify(status.payload) + ')', 'danger');
                    }
                },
                error(xhr, errorString, errorCode) {
                    notify('Could deliver', 'The stop command could not been send. (' + errorCode + ')', 'danger');
                }
            });

        } else {
            let id = $(this).data('slave-id');
            let el = $(this);

            $.ajax({
                type: 'GET',
                url: '/api/slave/' + id + '/wol',
                beforeSend(xhr) {
                    xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
                },
                converters: {
                    'text json': Status.from_json
                },
                success(status) {
                    if (status.is_ok()) {
                        el.addClass('animated pulse');
                        el.one('webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend', function () {
                            el.removeClass('animated pulse');
                        });
                    } else {
                        notify('Error while starting', 'Could not start client. (' + JSON.stringify(status.payload) + ')', 'danger');
                    }

                },
                error(xhr, errorString, errorCode) {
                    notify('Could deliver', 'The start command could not been send. (' + errorCode + ')', 'danger');
                }
            });

        }
    });

    //opens the slaveModal to add a new slave
    $('.slave-action-add').click(function () {
        let slaveModal = $('#slaveModal');
        slaveModal.children().find('.modal-title').text('Add Client');

        //modify the form for the submit button
        let slaveForm = slaveModal.children().find('#slaveForm');
        slaveForm.attr('action', '/api/slaves');
        slaveForm.attr('method', 'POST');
        slaveForm.children().find('.submit-btn').text('Add');

        //clear input fields
        slaveForm.find('[name="name"]').val('');
        slaveForm.find('[name="ip_address"]').val('');
        slaveForm.find('[name="mac_address"]').val('');

        //clear error messages
        clearErrorMessages(slaveForm);
        slaveModal.modal('toggle');

    });

    //opens the slaveModal to modify an existing slave
    $('.slave-action-modify').click(function () {
        //get info of slave
        let id = $(this).data('slave-id');
        let name = $(this).data('slave-name');
        let ip = $(this).data('slave-ip');
        let mac = $(this).data('slave-mac');

        let slaveModal = $('#slaveModal');
        slaveModal.children().find('.modal-title').text('Edit Client');

        //modify the form for the submit button
        let slaveForm = slaveModal.children().find('#slaveForm');
        slaveForm.attr('action', '/api/slave/' + id);
        slaveForm.attr('method', 'PUT');
        slaveForm.children().find('.submit-btn').text('Edit');

        //insert values into input field
        slaveForm.find('[name="name"]').val(name);
        slaveForm.find('[name="ip_address"]').val(ip);
        slaveForm.find('[name="mac_address"]').val(mac);

        //clear error messages
        clearErrorMessages(slaveForm);

        //open modal
        slaveModal.modal('toggle');
    });

    /*function for deleting a slave, it is added to the slave-action-delete button*/
    $('.slave-action-delete').click(function () {
        //get id and name of the slave and create deletion message
        let id = $(this).data('slave-id');
        let name = $(this).data('slave-name');

        let message = '<a>Are you sure you want to remove client </a><b>' + name + '</b>?</a>';

        prepareDeleteModal('Slave', id, message);
    });

    /*function for deleting a program, it is added to the program-action-delete
    button*/
    $('#deleteSlaveModalButton').click(function () {
        modalDeleteAction($('#slaveForm'), 'slave');
    });

    // slaveForm Handler
    $('#slaveForm').submit(onFormSubmit('slaveForm'));

    //register load and unload hooks for modals
    let hookModals = ['programModal', 'slaveModal', 'filesystemModal'];
    for (let modal of hookModals){
        $('#'+modal).on('show.bs.modal', function(e) {
            $(':input').on('input', function(e) {
            	window.unloadPrompt = true;
                removeAllChangeListener();
            });
            $('select').on('input', function(e) {
            	window.unloadPrompt = true;
                removeAllChangeListener();
            });
        });
        $('#'+modal).on('hidden.bs.modal', function(e) {
	    if (window.unloadPrompt){
            	$('#unsafedChangesWarning').data('parentModal', e.target.id);
            	$('#unsafedChangesWarning').modal('toggle');
	    }
            window.unloadPrompt = false;
    });
    }

    $('#keepParentModal').click(function(e) {
        let parentModal = $('#unsafedChangesWarning').data('parentModal');
        $('#unsafedChangesWarning').modal('toggle');
        $('#' + parentModal).modal('toggle');
    });

});

// global variable which determines the usage of the
// unload prompt
var unloadPrompt = false;

// if the site gets reloaded/closed all logging activity gets stopped
function logUnloadHandler() {
    $('.program-action-handle-logging').each(function () {
        if ($(this).data('enabled')) {
            let id = $(this).data('program-id');
            handleLogging(id, 'disable', false);
            $(this).data('enabled', false);
        }
    });
}

$(window).on('beforeunload', function (e) {
    logUnloadHandler();
    if (this.unloadPrompt) {
        let returnText = 'Are you sure you want to leave?';
        e.returnValue = returnText;
        return returnText;
    }
});

// if the site gets reloaded/closed all logging activity gets stopped
$(window).on('unload', function (e) {
    $('.program-action-handle-logging').each(function () {
        if ($(this).data('enabled')) {
            let id = $(this).data('program-id');
            handleLogging(id, 'disable', false);
            $(this).data('enabled', false);
        }
    });
});

function removeAllChangeListener(){
        $(':input').off('input');
        $('select').off('input');
}
