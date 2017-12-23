/**
 * Get a cookie by it the name. If the cookie is not present 'null' will be
 * returned.
 * @param {string} name Cookie name
 */
function getCookie(name) {
    if (document.cookie && document.cookie != '') {
        let cookie = document.cookie.split(',').find(function (raw_cookie) {
            let cookie = jQuery.trim(raw_cookie);
            return cookie.substring(0, name.length + 1) == (name + '=');
        });

        if (cookie != null) {
            return decodeURIComponent(cookie.substring(name.length + 1));
        }
    }
    return null;
}


/**
 * This function can be used for any kind delete actions. Insert the ID into the
 * #deleteWarning with .data('sqlId', id).
 *
 * @param {HTMLElement} form A valid HTML form.
 * @param {string} route A sub string of a valid REST route which accesses a
 * single object by it's id.
 */
function modalDeleteAction(form, route) {
    let id = $('#deleteWarning').data('sqlId');

    $.ajax({
        type: 'DELETE',
        url: '/api/' + route + '/' + id,
        beforeSend: function (xhr) {
            xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
        },
        converters: {
            'text json': Status.from_json
        },
        success: function (status) {
            if (status.is_ok()) {
                window.location.reload();
            } else {
                $.notify({
                    message: JSON.stringify(response.payload)
                }, {
                    type: 'danger'
                });
            }
        }
    });
}

/**
 * Handles the incoming status from a form request. The page will be reloaded or
 * the errors will be marked in the input field.
 *
 * @param {HTMLElement} form
 * @param {Status} status
 */
function handleFormStatus(form, status) {
    if (status.is_ok()) {
        console.log('OK');
        window.location.reload();
    } else {
        console.log('Err');
        console.log(status.to_json());
        // remove previous feedback
        form.find("div[class='invalid-feedback']").each(function (index, item) {
            item.remove();
        });

        // remove previous feedback
        form.find('.is-invalid').each(function (index, item) {
            $(item).removeClass('is-invalid');
        });

        // insert new feedback
        $.each(status.payload, function (id, msg) {
            let node = form.find('input[name=' + id + ']');
            node.addClass('is-invalid');
            node.parent().append("<div class='invalid-feedback'>" + msg + "</div>");
        });
    }
}

/**
 * Cleares the errorfields of a given form
 *
 * @param {HTMLElement} form
 */
function clearErrorMessages(form){
    form.find("div[class='invalid-feedback']").each(function (index, item) {
        item.remove();
    });

    form.find('.is-invalid').each(function (index, item) {
        $(item).removeClass('is-invalid');
    });
}


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

    // Enable tool tips.
    $(function () {
        $("[data-toggle='tooltip']").tooltip()
    });

    /*function for deleting a slave, it is added to the delete_slave button*/
    $('.delete_slave').click(function () {

        //get id and name of the slave and create deletion message
        let id = $(this).parents('.slave-card').attr('id');
        let name = $(this).parents('.slave-card').children().find('.slave-name').text();
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

    /*function for deleting a program, it is added to the delete_program button*/
    $('.delete_program').click(function () {
        //get id and name of the program and create deletion message
        let id = $(this).parents('.program-card').attr('data-id');
        let name = $(this).parents('.program-card').children().find('.program-name').text();
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
        modalDeleteAction($('#programForm'), 'program')
    });

    $('.start-program-btn').click(function () {
        let id = $(this).parents('.program-card').attr('data-id');
        $.ajax({
            type: 'POST',
            url: '/api/program/' + id,
            beforeSend: function (xhr) {
                xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
            },
            converters: {
                'text json': Status.from_json
            },
            success: function (status) {
                if (status.is_err()) {
                    $.notify({
                        message: status.payload
                    }, {
                        type: 'danger'
                    });
                }
            },
            error: function () {
                $.notify({
                    message: 'Error in Ajax Request.'
                }, {
                    type: 'danger'
                });
            }
        });
    });

    //opens the programModal to add a new program
    $('.add-program-btn').click(function () {
        let programModal = $('#programModal');
        programModal.children().find('.modal-title').text('Add Program');


        //modify the form for the submit button
        let programForm = programModal.children().find('#programForm');
        programForm.attr('action', '/api/programs');
        programForm.attr('method', 'POST');
        programForm.children().find('.submit-btn').text('Add');

        //clear input fields
        programForm.find("input[name='name']").val('');
        programForm.find("input[name='path']").val('');
        programForm.find("input[name='arguments']").val('');

        //clear error messages
        clearErrorMessages(programForm);

        //find slave id and store it in the form
        let card = $(this).parents('.slave-card');
        programForm.find("input[name='slave']").val(card.attr('id'));

        programModal.modal('toggle');
    });

    //opens the programModal to modify a program
    $('.modify-program-btn').click(function () {
        let programModal = $('#programModal');
        let programForm = programModal.children().find('#programForm');

        //get info of program
        let card = $(this).parents('.program-card');
        let id = card.attr('data-id');
        let name = card.children().find('.program-name').text().trim();
        let path = card.children().find('.program-path').text().trim();
        let args = card.children().find('.program-arguments').text().trim();

        console.log('id:' + id + ' name:' + name + ' path:' + path + ' args:' + args);

        //modify the form for the submit button
        programModal.children().find('.modal-title').text('Edit Program');
        programForm.attr('action', '/api/program/' + id);
        programForm.attr('method', 'PUT');
        programForm.children().find('.submit-btn').text('Edit');

        //clear input fields
        programForm.find("input[name='name']").val(name);
        programForm.find("input[name='path']").val(path);
        programForm.find("input[name='arguments']").val(args);

        //clear error messages
        clearErrorMessages(programForm);

        //find slave id and store it in the form
        let slaveCard = $(this).parents('.slave-card');
        programForm.find("input[name='slave']").val(slaveCard.attr('id'));


        //find slave id and store it in the form
        programModal.modal('toggle');
    });

    //opens the slaveModal to add a new slave
    $('.add-slave-btn').click(function () {
        let slaveModal = $('#slaveModal');
        slaveModal.children().find('.modal-title').text('Add Client');

        //modify the form for the submit button
        let slaveForm = slaveModal.children().find('#slaveForm');
        slaveForm.attr('action', '/api/slaves');
        slaveForm.attr('method', 'POST');
        slaveForm.children().find('.submit-btn').text('Add');

        //clear input fields
        slaveForm.find("input[name='name']").val('');
        slaveForm.find("input[name='ip_address']").val('');
        slaveForm.find("input[name='mac_address']").val('');

        //clear error messages
        clearErrorMessages(slaveForm);

        slaveModal.modal('toggle');
    });

    //opens the slaveModal to modify an existing slave
    $('.modify-slave-btn').click(function () {
        //get info of slave
        let card = $(this).parents('.card');
        let id = card.attr('id');
        let name = card.children().find('.slave-name').text().trim();
        let ip = card.children().find('.slave-ip').text().trim();
        let mac = card.children().find('.slave-mac').text().trim();

        let slaveModal = $('#slaveModal');
        slaveModal.children().find('.modal-title').text('Edit Client');

        //modify the form for the submit button
        let slaveForm = slaveModal.children().find('#slaveForm');
        slaveForm.attr('action', '/api/slave/' + id);
        slaveForm.attr('method', 'PUT');
        slaveForm.children().find('.submit-btn').text('Edit');

        //insert values into input field
        slaveForm.find("input[name='name']").val(name);
        slaveForm.find("input[name='ip_address']").val(ip);
        slaveForm.find("input[name='mac_address']").val(mac);

        //clear errormessages
        clearErrorMessages(slaveForm);

        //open modal
        slaveModal.modal('toggle');
    });

    // programForm Handler
    $('#programForm').submit(function (event) {
        //Stop form from submitting normally
        event.preventDefault();
        console.log($(this).serialize());

        //send request to given url and with given method
        //data field contains information about the slave
        $.ajax({
            type: $(this).attr('method'),
            url: $(this).attr('action'),
            data: $(this).serialize(),
            converters: {
                'text json': Status.from_json
            },
            beforeSend: function (xhr) {
                xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
            },
            success: function (status) {
                handleFormStatus($('#programForm'), status);
            },
            error: function () {
                $.notify({
                    message: 'Error in Ajax Request.'
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
            beforeSend: function (xhr) {
                xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
            },
            converters: {
                'text json': Status.from_json
            },
            success: function (status) {
                handleFormStatus($('#slaveForm'), status);
            },
            error: function () {
                $.notify({
                    message: 'Error in Ajax Request.'
                }, {
                    type: 'danger'
                });
            }
        });
    });

    $('.startSlave').click(function () {
        let id = $(this).parents('.card').attr('id');
        let el = $(this);
        $.get({
            url: '/api/slave/' + id + '/wol',
            beforeSend: function (xhr) {
                xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'))
            }
        }).done(function (data) {
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
        }).fail(function () {
            $.notify({
                message: 'Error in Ajax Request.'
            }, {
                type: 'danger'
            });
        });
    });
});
