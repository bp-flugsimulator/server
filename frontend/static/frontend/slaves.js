/**
 * Get a cookie by it the name. If the cookie is not present "null" will be
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
 * Displays an error in the alert container. For a specific collapse.
 * @param {int} id Collapse ID
 * @param {string} err Error message
 */
function displayError(id, err) {
    $('#collapse' + id).append('<div class="alert alert-danger"><strong>Error!</strong> ' + err + '</div>');
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
    var id = $('#deleteWarning').data('sqlId');

    $.ajax({
        type: 'DELETE',
        url: '/api/' + route + '/' + id,
        beforeSend: function (xhr) {
            xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        },
        converters: {
            "text json": Status.from_json
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
        console.log("OK");
        window.location.reload();
    } else {
        console.log("Err");
        console.log(status.to_json());
        // remove previous feedback
        form.find("div[class='invalid-feedback']").each(function (index, item) {
            item.remove();
        });

        // remove previous feedback
        form.find(".is-invalid").each(function (index, item) {
            $(item).removeClass("is-invalid");
        });

        // insert new feedback
        $.each(status.payload, function (id, msg) {
            var node = form.find("input[name=" + id + "]");
            node.addClass("is-invalid");
            node.parent().append('<div class="invalid-feedback">' + msg + '</div>');
        });
    }
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
        $('[data-toggle="tooltip"]').tooltip()
    });

    /*function for deleting a slave, it is added to the delete_slave button*/
    $(".delete_slave").click(function () {

        //get id and name of the slave and create deletion message
        var id = $(this).parents(".slave-card").attr("id");
        var name = $(this).parents(".slave-card").children().find('.slave-name').text();
        var message = "<a>Are you sure you want to remove client </a><b>" + name + "</b>?</a>";

        //changing button visibility and message of the delete modal
        $('#deleteWarning .modal-footer #deleteProgramModalButton').hide();
        $('#deleteWarning .modal-footer #deleteSlaveModalButton').show();
        $('#deleteWarning .modal-body').empty(message);
        $('#deleteWarning .modal-body').append(message);


        //adding id to modal and set it visible
        $('#deleteWarning').data('sqlId', id);
        $('#deleteWarning').modal('toggle');
    });

    /*function for deleting a program, it is added to the delete_program button*/
    $(".delete_program").click(function () {

        //get id and name of the program and create deletion message
        var id = $(this).parents(".program-card").attr("data-id");
        var name = $(this).parents(".program-card").children().find('.program-name').text();
        var message = "<a>Are you sure you want to remove program </a><b>" + name + "</b>?</a>";

        //changing button visibility and message of the delete modal
        $('#deleteWarning .modal-footer #deleteSlaveModalButton').hide();
        $('#deleteWarning .modal-footer #deleteProgramModalButton').show();
        $('#deleteWarning .modal-body').empty(message);
        $('#deleteWarning .modal-body').append(message);

        //adding id to modal and set it visible
        $('#deleteWarning').data('sqlId', id);
        $('#deleteWarning').modal('toggle');

    });

    $('#deleteSlaveModalButton').click(function () {
        modalDeleteAction($('#slaveForm'), "slave");
    });

    $('#deleteProgramModalButton').click(function () {
        modalDeleteAction($('#programForm'), "program")
    });

    $('.start-program-btn').click(function () {
        var id = $(this).parents(".program-card").attr("data-id");
        $.ajax({
            type: 'POST',
            url: '/api/program/' + id,
            beforeSend: function (xhr) {
                xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
            },
            converters: {
                "text json": Status.from_json
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
        programModal = $('#programModal');
        programModal.children().find('.modal-title').text("Add Program");


        //modify the form for the submit button
        programForm = programModal.children().find('#programForm');
        programForm.attr('action', '/api/programs');
        programForm.attr('method', 'POST');
        programForm.children().find('.submit-btn').text('Add');

        //clear input fields
        programForm.find("input[name='name']").val("");
        programForm.find("input[name='path']").val("");
        programForm.find("input[name='arguments']").val("");

        //clear error messages
        programForm.find("div[class='invalid-feedback']").each(function (index, item) {
            item.remove();
        });
        programForm.find(".is-invalid").each(function (index, item) {
            $(item).removeClass("is-invalid");
        });

        //find slave id and store it in the form
        var card = $(this).parents('.slave-card');
        programForm.find("input[name='slave']").val(card.attr("id"));

        programModal.modal('toggle');
    });

    //opens the programModal to modify a program
    $('.modify-program-btn').click(function () {
        programModal = $('#programModal');
        programForm = programModal.children().find('#programForm');

        //get info of program
        var card = $(this).parents('.program-card');
        var id = card.attr('data-id');
        var name = card.children().find('.program-name').text().trim();
        var path = card.children().find('.program-path').text().trim();
        var args = card.children().find('.program-arguments').text().trim();

        console.log("id:" + id + " name:" + name + " path:" + path + " args:" + args);

        //modify the form for the submit button
        programModal.children().find('.modal-title').text("Edit Program");
        programForm.attr('action', '/api/program/' + id);
        programForm.attr('method', 'PUT');
        programForm.children().find('.submit-btn').text('Edit');

        //clear input fields
        programForm.find("input[name='name']").val(name);
        programForm.find("input[name='path']").val(path);
        programForm.find("input[name='arguments']").val(args);

        //clear errormessages
        programForm.find("div[class='invalid-feedback']").each(function (index, item) {
            item.remove();
        });
        programForm.find(".is-invalid").each(function (index, item) {
            $(item).removeClass("is-invalid");
        });

        //find slave id and store it in the form
        programModal.modal('toggle');
    });

    //opens the slaveModal to add a new slave
    $('.add-slave-btn').click(function () {
        slaveModal = $('#slaveModal');
        slaveModal.children().find('.modal-title').text("Add Client");

        //modify the form for the submit button
        slaveForm = slaveModal.children().find('#slaveForm');
        slaveForm.attr('action', '/api/slaves');
        slaveForm.attr('method', 'POST');
        slaveForm.children().find('.submit-btn').text('Add');

        //clear input fields
        slaveForm.find("input[name='name']").val("");
        slaveForm.find("input[name='ip_address']").val("");
        slaveForm.find("input[name='mac_address']").val("");

        //clear errormessages
        slaveForm.find("div[class='invalid-feedback']").each(function (index, item) {
            item.remove();
        });
        slaveForm.find(".is-invalid").each(function (index, item) {
            $(item).removeClass("is-invalid");
        });

        slaveModal.modal('toggle');
    });

    //opens the slaveModal to modify an existing slave
    $('.modify-slave-btn').click(function () {
        //get info of slave
        var card = $(this).parents('.card');
        var id = card.attr("id");
        var name = card.children().find('.slave-name').text().trim();
        var ip = card.children().find('.slave-ip').text().trim();
        var mac = card.children().find('.slave-mac').text().trim();

        var slaveModal = $('#slaveModal');
        slaveModal.children().find('.modal-title').text("Edit Client");

        //modify the form for the submit button
        var slaveForm = slaveModal.children().find('#slaveForm');
        slaveForm.attr('action', '/api/slave/' + id);
        slaveForm.attr('method', 'PUT');
        slaveForm.children().find('.submit-btn').text('Edit');

        //insert values into input field
        slaveForm.find("input[name='name']").val(name);
        slaveForm.find("input[name='ip_address']").val(ip);
        slaveForm.find("input[name='mac_address']").val(mac);

        //clear errormessages
        slaveForm.find("div[class='invalid-feedback']").each(function (index, item) {
            item.remove();
        });
        slaveForm.find(".is-invalid").each(function (index, item) {
            $(item).removeClass("is-invalid");
        });

        //open modal
        slaveModal.modal('toggle');
    });

    // programForm Handler
    $('#programForm').submit(function (event) {
        //Stop form from submitting normally
        event.preventDefault();
        console.log($('#programForm').serialize());

        //send request to given url and with given method
        //data field contains information about the slave
        $.ajax({
            type: $(this).attr('method'),
            url: $(this).attr('action'),
            data: $('#programForm').serialize(),
            converters: {
                "text json": Status.from_json
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
                "text json": Status.from_json
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
        var id = $(this).parents('.card').attr("id");
        var el = $(this);
        $.get({
            url: '/api/slave/' + id + '/wol',
            beforeSend: function (xhr) {
                xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'))
            }
        }).done(function (data) {
            var status = Status.from_json(JSON.stringify(data));
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

    // Save Class when opening/closing accordion for every Slave
    $('#accordion').children().each(function () {
        var child_id = this.id;
        var collapse_id = "#collapse" + child_id;
        var status = "collapseStatus" + child_id;

        $(collapse_id).on('show.bs.collapse', function () {
            localStorage.setItem(status, "show");
            $('div[href="' + collapse_id + '"]').children(".btn")
                .attr('data-original-title', "Show Less")
                .tooltip('show')
                .html('<i class="material-icons">expand_less</i>');
        });
        $(collapse_id).on('hide.bs.collapse', function () {
            localStorage.setItem(status, "");
            $('div[href="' + collapse_id + '"]').children()
                .attr('data-original-title', "Show More")
                .tooltip('show')
                .html('<i class="material-icons">expand_more</i>');
        });
        // restore saved class
        $(collapse_id).addClass(localStorage.getItem(status));
    });

    // fixes the tooltip from staying after button is pressed
    $('[data-toggle="tooltip"]').tooltip({
        trigger: 'hover'
    })
});
