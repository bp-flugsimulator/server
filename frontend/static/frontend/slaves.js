/* eslint-env browser*/
/* global $, getCookie, modalDeleteAction, handleFormStatus, clearErrorMessages, Status */

$(document).ready(function () {
    // set defaults for notifications
    $.notifyDefaults({
        type: 'success',
        placement: {
            from: 'bottom',
            align: 'right'
        },
        animate: {
            enter: 'animated fadeInRight',
            exit: 'animated fadeOutRight'
        }
    });

    // Restores the last clicked slave
    (function () {
        let href = localStorage.getItem('status');
        if (href !== null) {
            let iter = $('.slave-tab-link').filter(function (idx, val) {
                return val.hasAttribute('href') && val.getAttribute('href') === href;
            });

            iter.click();
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

    /*function for deleting a slave, it is added to the delete-slave button*/
    $('.delete-slave').click(function () {
        //get id and name of the slave and create deletion message
        let id = $(this).data('slave-id');
        let name = $(this).data('slave-name');

        let message = '<a>Are you sure you want to remove client </a><b>' + name + '</b>?</a>';

        //changing button visibility and message of the delete modal
        let deleteWarning = $('#deleteWarning');
        deleteWarning.children().find('#deleteProgramModalButton').hide();
        deleteWarning.children().find('#deleteSlaveModalButton').show();
        deleteWarning.children().find('.modal-body').empty(message);
        deleteWarning.children().find('.modal-body').append(message);


        //adding id to modal and set it visible
        deleteWarning.data('sqlId', id);
        deleteWarning.modal('toggle');
    });

    /*function for deleting a program, it is added to the delete-program button*/
    $('.delete-program').click(function () {
        //get id and name of the program and create deletion message
        let id = $(this).data('program-id');
        let name = $(this).data('program-name');
        let message = '<a>Are you sure you want to remove program </a><b>' + name + '</b>?</a>';

        //
        //changing button visibility and message of the delete modal
        let deleteWarning = $('#deleteWarning');
        deleteWarning.children().find('#deleteSlaveModalButton').hide();
        deleteWarning.children().find('#deleteProgramModalButton').show();
        deleteWarning.children().find('.modal-body').empty(message);
        deleteWarning.children().find('.modal-body').append(message);


        //adding id to modal and set it visible
        deleteWarning.data('sqlId', id);
        deleteWarning.modal('toggle');
    });

    $('#deleteSlaveModalButton').click(function () {
        modalDeleteAction($('#slaveForm'), 'slave');
    });

    $('#deleteProgramModalButton').click(function () {
        modalDeleteAction($('#programForm'), 'program');
    });

    $('.start-program').click(function () {
        let id = $(this).data('program-id');
        $.ajax({
            type: 'POST',
            url: '/api/program/' + id,
            beforeSend(xhr) {
                xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
            },
            converters: {
                'text json': Status.from_json
            },
            success(status) {
                if (status.is_err()) {
                    $.notify({
                        message: status.payload
                    }, {
                            type: 'danger'
                        });
                }
            },
            error(xhr, errorString, errorCode) {
                $.notify({
                    message: 'Could not deliver delete request to server (' + errorCode + ')'
                }, {
                        type: 'danger'
                    });
            }
        });
    });

    //opens the programModal to add a new program
    $('.add-program').click(function () {
        let programModal = $('#programModal');
        programModal.children().find('.modal-title').text('Add Program');

        //modify the form for the submit button
        let programForm = programModal.children().find('#programForm');
        programForm.attr('action', '/api/programs');
        programForm.attr('method', 'POST');
        programForm.children().find('.submit-btn').text('Add');

        //clear input fields

        programForm.find('input[name="name"]').val('');
        programForm.find('input[name="path"]').val('');
        programForm.find('input[name="arguments"]').val('');

        //clear error messages
        clearErrorMessages(programForm);

        //find slave id and store it in the form
        let slaveId = $(this).data('slave-id');
        programForm.find('input[name="slave"]').val(slaveId);
        programModal.modal('toggle');
    });

    //opens the programModal to modify a program
    $('.modify-program').click(function () {
        let programModal = $('#programModal');
        let programForm = programModal.children().find('#programForm');

        //get info of program
        let id = $(this).data('program-id');
        let name = $(this).data('program-name');
        let path = $(this).data('program-path');
        let args = $(this).data('program-arguments');

        //modify the form for the submit button
        programModal.children().find('.modal-title').text('Edit Program');
        programForm.attr('action', '/api/program/' + id);
        programForm.attr('method', 'PUT');
        programForm.children().find('.submit-btn').text('Edit');

        //clear input fields
        programForm.find('input[name="name"]').val(name);
        programForm.find('input[name="path"]').val(path);
        programForm.find('input[name="arguments"]').val(args);

        //clear error messages
        clearErrorMessages(programForm);

        //find slave id and store it in the form
        let slaveId = $(this).data('slave-id');
        programForm.find('input[name="slave"]').val(slaveId);

        //find slave id and store it in the form
        programModal.modal('toggle');
    });

    //opens the fileModal to add a new program
    $('.add-file').click(function () {
        let fileModal = $('#fileModal');
        fileModal.children().find('.modal-title').text('Add File');

        //modify the form for the submit button
        let fileForm = fileModal.children().find('#fileForm');
        fileForm.attr('action', '/api/files');
        fileForm.attr('method', 'POST');
        fileForm.children().find('.submit-btn').text('Add');

        //clear input fields
        fileForm.find('input[name="name"]').val('');
        fileForm.find('input[name="sourcePath"]').val('');
        fileForm.find('input[name="destinationPath"]').val('');

        //clear error messages
        clearErrorMessages(fileForm);

        //find slave id and store it in the form
        let slaveId = $(this).data('slave-id');
        fileForm.find('input[name="slave"]').val(slaveId);
        fileModal.modal('toggle');
    });

    //opens the slaveModal to add a new slave
    $('.add-slave').click(function () {
        let slaveModal = $('#slaveModal');
        slaveModal.children().find('.modal-title').text('Add Client');

        //modify the form for the submit button
        let slaveForm = slaveModal.children().find('#slaveForm');
        slaveForm.attr('action', '/api/slaves');
        slaveForm.attr('method', 'POST');
        slaveForm.children().find('.submit-btn').text('Add');

        //clear input fields
        slaveForm.find('input[name="name"]').val('');
        slaveForm.find('input[name="ip_address"]').val('');
        slaveForm.find('input[name="mac_address"]').val('');

        //clear error messages
        clearErrorMessages(slaveForm);
        slaveModal.modal('toggle');
    });

    //opens the slaveModal to modify an existing slave
    $('.modify-slave').click(function () {
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
        slaveForm.find('input[name="name"]').val(name);
        slaveForm.find('input[name="ip_address"]').val(ip);
        slaveForm.find('input[name="mac_address"]').val(mac);

        //clear error messages
        clearErrorMessages(slaveForm);

        //open modal
        slaveModal.modal('toggle');
    });

    // programForm Handler
    $('#programForm').submit(function (event) {
        //Stop form from submitting normally
        event.preventDefault();

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
                handleFormStatus($('#programForm'), status);
            },
            error(xhr, errorString, errorCode) {
                $.notify({
                    message: 'Could not deliver ' + $(this).attr('method') + ' request to server (' + errorCode + ')'
                }, {
                        type: 'danger'
                    });
            }
        });
    });

    // fileForm Handler
    $('#fileForm').submit(function (event) {
        //Stop form from submitting normally
        event.preventDefault();

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
                handleFormStatus($('#fileForm'), status);
            },
            error(xhr, errorString, errorCode) {
                $.notify({
                    message: 'Could not deliver ' + $(this).attr('method') + ' request to server (' + errorCode + ')'
                }, {
                        type: 'danger'
                    });
            }
        });
    });

    // slaveForm Handler
    $('#slaveForm').submit(function (event) {
        //Stop form from submitting normally
        event.preventDefault();
        //send request to given url and with given method
        //data field contains information about the slave
        $.ajax({
            type: $(this).attr('method'),
            url: $(this).attr('action'),
            data: $('#slaveForm').serialize(),
            beforeSend(xhr) {
                xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
            },
            converters: {
                'text json': Status.from_json
            },
            success(status) {
                handleFormStatus($('#slaveForm'), status);
            },
            error(xhr, errorString, errorCode) {
                $.notify({
                    message: 'Could not deliver ' + $(this).attr('method') + ' request to server (' + errorCode + ')'
                }, {
                        type: 'danger'
                    });
            }
        });
    });

    $('.start-slave').click(function () {
        let id = $(this).data('slave-id');
        let el = $(this);

        $.ajax({
            type: 'GET',
            url: '/api/slave/' + id + '/wol',
            beforeSend(xhr) {
                xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
            },
            success(data) {
                let status = Status.from_json(JSON.stringify(data));
                if (status.is_ok()) {
                    el.addClass('animated pulse');
                    el.one('webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend', function () {
                        el.removeClass('animated pulse');
                    });
                } else {
                    $.notify({
                        message: 'Error: ' + data.payload
                    }, {
                            type: 'danger'
                        });
                }

            },
            error(xhr, errorString, errorCode) {
                $.notify({
                    message: 'Could not deliver Wake-On-Lan request to server (' + errorCode + ')'
                }, {
                        type: 'danger'
                    });
            }
        });
    });

    $('.stop-slave').click(function () {
        let id = $(this).data('slave-id');
        let el = $(this);

        $.ajax({
            type: 'GET',
            url: '/api/slave/' + id + '/shutdown',
            beforeSend(xhr) {
                xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
            },
            success(data) {
                let status = Status.from_json(JSON.stringify(data));
                if (status.is_ok()) {
                    el.addClass('animated pulse');
                    el.one('webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend', function () {
                        el.removeClass('animated pulse');
                    });
                } else {
                    $.notify({
                        message: 'Error: ' + data.payload
                    }, {
                            type: 'danger'
                        });
                }
            },
            error(xhr, errorString, errorCode) {
                $.notify({
                    message: 'Could not deliver shutdown request to server (' + errorCode + ')'
                }, {
                        type: 'danger'
                    });
            }
        });
    });

    // fixes the tooltip from staying after button is pressed
    $('[data-toggle="tooltip"]').tooltip({
        trigger: 'hover',
        'delay': {
            show: 100,
            hide: 300
        }
    });
});
