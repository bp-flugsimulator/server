/* eslint-env browser*/
/* eslint no-use-before-define: ['error', { 'functions': false }] */
/* global $, modalDeleteAction, clearErrorMessages, fsimWebsocket, swapText,
 styleSlaveByStatus, basicRequest, AnsiTerm */
/* exported unloadPrompt */

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
        basicRequest({
            type: $(this).attr('method'),
            url: $(this).attr('action'),
            data: $(this).serialize(),
            onSuccess() {
                window.location.reload();
            },
            onError(payload) {
                let form = $('#' + id);
                clearErrorMessages(form);

                // insert new feedback
                $.each(payload, function (id, msg) {
                    let node = form.find('[name=' + id + ']');
                    node.addClass('is-invalid');
                    node.parent().append('<div class="invalid-feedback">' + msg + '</div>');
                });
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

function handleLogging(id, method) {
    basicRequest({
        type: 'POST',
        url: '/api/program/' + id + '/log/' + method,
        action: method + ' log',
    });
}

function checkFormRequired(elem) {
    let reqEmpty = false;
    $(elem).parent().parent().find('.form-control').each(function (i, val) {
        if (val.value === '' && $(val).attr('required')) {
            reqEmpty = true;
        }
    });
    $('.submit-btn').prop('disabled', reqEmpty);
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

        statusContainer.attr('data-state', 'running');
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

    // Select color after reload
    $('.slave-content-tab.active').removeClass('text-dark bg-light')
        .addClass('text-light bg-dark')
        .children('button').removeClass('btn-dark')
        .addClass('btn-light');

    $('.slave-content-tab').click(function () {
        if (!$(this).hasClass('active')) {
            // Remove color from the old tabs
            $('.slave-content-tab').each(function (idx, val) {
                $(val).removeClass('bg-dark text-light')
                    .addClass('text-dark')
                    .children('button').removeClass('btn-light')
                    .addClass('btn-dark');
            });

            // Save Class when opening for every Slave
            localStorage.setItem('status-tabs', $(this).attr('href'));

            // Change the color of the current tab
            $(this).removeClass('text-dark')
                .addClass('bg-dark text-light')
                .children('button').removeClass('btn-dark')
                .addClass('btn-light');
        }
    });

    // Set color of the current selected.
    $('.slave-tab-link.active').addClass('border-dark bg-dark text-light')
        .children('span').removeClass('badge-dark')
        .addClass('badge-light');

    // Changes the color of the clicked slave, if it was not clicked before.
    $('.slave-tab-link').click(function () {
        if (!$(this).hasClass('active')) {
            // Remove color from the old tabs
            $('.slave-tab-link').each(function (idx, val) {
                $(val).removeClass('border-dark bg-dark text-light')
                    .addClass('text-dark')
                    .children('span').removeClass('badge-light')
                    .addClass('badge-dark');
            });

            // Save Class when opening for every Slave
            localStorage.setItem('status', $(this).attr('href'));

            // Change the color of the current tab
            $(this).removeClass('text-dark')
                .addClass('border-dark bg-dark text-light')
                .children('span').removeClass('badge-dark')
                .addClass('badge-light');
        }
        $('.slave-content-tab.active').removeClass('text-dark bg-light')
            .addClass('text-light bg-dark')
            .children('button').removeClass('btn-dark')
            .addClass('btn-light');
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
        let apiRequest = function (url, type, action) {
            basicRequest({
                type: type,
                url: url,
                action: action,
            });
        };

        let id = $(this).data('program-id');

        let cardButton = $('#programCardButton_' + id);
        cardButton.prop('disabled', false);

        if ($(this).attr('data-is-running') === 'True') {
            apiRequest('/api/program/' + id + '/stop', 'POST', 'stop program');
        } else if ($(this).attr('data-is-running') === 'False') {
            apiRequest('/api/program/' + id + '/start', 'POST', 'start program');
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
        programForm.children().find('.submit-btn').text('Apply');

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
        filesystemModal.children().find('.modal-title').text('Add Filesystem');

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
        let source_type = $(this).data('filesystem-source_type');
        let destination_type = $(this).data('filesystem-destination_type');

        //modify the form for the submit button
        filesystemModal.children().find('.modal-title').text('Edit Filesystem');
        filesystemForm.attr('action', '/api/filesystem/' + id);
        filesystemForm.attr('method', 'PUT');
        filesystemForm.children().find('.submit-btn').text('Apply');

        //set values into input fields
        filesystemForm.find('[name="name"]').val(name);
        filesystemForm.find('[name="source_path"]').val(sourcePath);
        filesystemForm.find('[name="destination_path"]').val(destinationPath);
        filesystemForm.find('[name="source_type"]').val(source_type);
        filesystemForm.find('[name="destination_type"]').val(destination_type);


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
            basicRequest({
                url: '/api/filesystem/' + id + '/restore',
                type: 'POST',
                action: 'restore entry in filesystem',
            });
        } else if ($(this).attr('data-is-moved') === 'False') {
            basicRequest({
                url: '/api/filesystem/' + id + '/move',
                type: 'POST',
                action: 'move entry in filesystem'
            });
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

            basicRequest({
                type: 'POST',
                url: '/api/slave/' + id + '/shutdown',
                action: 'stop client'
            });

        } else {
            let id = $(this).data('slave-id');

            basicRequest({
                type: 'POST',
                url: '/api/slave/' + id + '/wol',
                action: 'start client'
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
        slaveForm.children().find('.submit-btn').text('Apply');

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
    for (let modal of hookModals) {
        $('#'+modal).on('show.bs.modal', function() {
            $(':input').on('input', function() {
                window.unloadPrompt = true;
                removeAllChangeListener();
            });

            $('select').on('input', function() {
                window.unloadPrompt = true;
                removeAllChangeListener();
            });
        });

        $('#'+modal).on('hidden.bs.modal', function(e) {
            if (window.unloadPrompt) {
                $('#unsafedChangesWarning').data('parentModal', e.target.id);
                $('#unsafedChangesWarning').modal('toggle');
            }
            window.unloadPrompt = false;
        });
    }

    $('.keepParentModal').click(function() {
        let parentModal = $('#unsafedChangesWarning').data('parentModal');
        $('#unsafedChangesWarning').modal('toggle');
        $('#' + parentModal).modal('toggle');
    });

    // Disable Modal Submit Button if nothing changed or a field is empty
    $('.submit-btn').prop('disabled', true);
    $('.form-control').on('change keyup', function () {
        checkFormRequired(this);
    });
});

// global variable which determines the usage of the unload prompt
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
$(window).on('unload', function () {
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
