/* eslint-env browser */
/* eslint no-use-before-define: ["error", { "functions": false }] */
/* global $, jQuery, Status */
/* exported  getCookie, modalDeleteAction, clearErrorMessages,swapText, styleSlaveByStatus, notify, basicRequest */

/**
 * Clears the error fields of a given form
 *
 * @param {HTMLElement} form
 *
 */
function clearErrorMessages(form) {
    // remove previous feedback
    form.find('div[class="invalid-feedback"]').each(function (index, item) {
        item.remove();
    });

    // remove previous feedback
    form.find('.is-invalid').each(function (index, item) {
        $(item).removeClass('is-invalid');
    });
}

/**
 * Get a cookie by it the name. If the cookie is not present 'null' will be
 * returned.
 * @param {string} name Cookie name
 *
 */
function getCookie(name) {
    if (document.cookie && document.cookie !== '') {
        let cookie = document.cookie.split(',').find(function (rawCookie) {
            let cookie = jQuery.trim(rawCookie);
            return cookie.substring(0, name.length + 1) === (name + '=');
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
 *
 */
function modalDeleteAction(form, route) {
    let id = $('#deleteWarning').data('sqlId');

    $.ajax({
        type: 'DELETE',
        url: '/api/' + route + '/' + id,
        beforeSend(xhr) {
            xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
        },
        converters: {
            'text json': Status.from_json
        },
        success(status) {
            if (status.is_ok()) {
                window.location.reload();
            } else {
                $('#deleteWarning').modal('toggle');

                notify(
                    'Error while deleting',
                    JSON.stringify(status.payload),
                    'danger'
                );
            }
        },
        error(xhr, errorString, errorCode) {
            notify(
                'Transport error',
                'Could not deliver delete request to server (' + errorCode + ')',
                'danger'
            );
        }
    });
}

/**
 * Swaps the text with the data-text-swap field.
 *
 * @param {HTMLElement} form
 * @param {Status} status
 *
 */
function swapText(element) {
    if (element.text() === element.data('text-swap')) {
        element.text(element.data('text-original'));
    } else {
        element.data('text-original', element.text());
        element.text(element.data('text-swap'));
    }
}

/**
 * Styles a slave tab and container by the status of their programs.
 * @param {Integer} sid slave id
 * @param {Boolean} error If it is error related.
 * @param {Boolean} up Count up or down.
 */
function styleSlaveByStatus(sid, error, e_up, success, s_up) {
    let statusContainer = $('#slaveStatusContainer_' + sid);
    let statusTab = $('#slaveTab' + sid);

    let style = function(boolean) {
        return function (idx, elem) {
            let element = $(elem);

            let attr = element.attr('data-value');
            let num = parseInt(attr, 10);
            if (boolean) {
                num += 1;
            } else {
                num -= 1;
            }
            element.attr('data-value', num);
        };
    };

    if (success === undefined) {
        success = false;
    }

    if (error) {
        statusContainer.find('[name=status-badge-errored][data-value]').each(style(e_up));
        statusTab.find('[name=status-badge-errored][data-value]').each(style(e_up));
    }

    if (success) {
        statusContainer.find('[name=status-badge-running][data-value]').each(style(s_up));
        statusTab.find('[name=status-badge-running][data-value]').each(style(s_up));
    }
}

/**
 * Spawns a notification box for the user where the given information are
 * displayed.
 *
 * @param {String} title The title in the message box
 * @param {String} message The body message in the message box
 * @param {['danger'|'warning'|'info']} type The type or color of the message
 * box
 */
function notify(title, message, type) {
    $.notify({
        title,
        message,
    },
    {
        type,
        template: '<div data-notify="container" class="col-11 col-sm-3 alert" role="alert" data-notify-type="{0}">' +
            '<button type="button" aria-hidden="true" class="close" data-notify="dismiss">×</button>' +
            '<div class="col">' +
            '<span class="row" data-notify="title">' +
            '<strong>{1}</strong>' +
            '</span>' +
            '<span class="row text-justify" data-notify="message">{2}</span>' +
            '</div>' +
            '</div>'
    });
}

/**
 * Performs a basic request which does not need a direct response.
 * @param {String} url URL path to the server
 * @param {String} type  HTTP request type
 * @param {String} action Determines the kind of action which this request performs
 * @param {Object} data HTTP data (e.g. POST request)
 * @param {Function(payload)} onSuccess function that gets called on success
 * @param {Function(payload)} onError function that gets called if  an error occurs
 */
function basicRequest(options) {
    if (options.data === undefined) {
        options.data = {};
    }

    $.ajax({
        type: options.type,
        url: options.url,
        data: options.data,
        beforeSend(xhr) {
            xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
        },
        converters: {
            'text json': Status.from_json
        },
        success: function(status) {
            if (status.is_ok()) {
                if (options.onSuccess !== undefined) {
                    options.onSuccess(status.payload);
                }
            } else {
                if (options.onError !== undefined) {
                    options.onError(status.payload);
                } else {
                    notify('Error while' + options.action, JSON.stringify(status.payload), 'danger');
                }
            }
        },
        error: function(xhr, errorString, errorCode) {
            notify('HTTP request error', 'Could not deliver request `' + options.action + '` to the server.\nReason:\n' + errorCode + ')', 'danger');
        }
    });
}

$(document).ready(function () {
    $.notifyDefaults({
        type: 'success',
        delay: 5000,
        newest_on_top: true,
        showProgressbar: false,
        placement: {
            from: 'top',
            align: 'right'
        },
        animate: {
            enter: 'animated fadeInRight',
            exit: 'animated fadeOutRight'
        },
    });

    var enableSubmit = function (ele) {
        $(ele).removeAttr('disabled');
    };

    $('.short-disable').click(function () {
        var that = this;
        $(this).attr('disabled', true);
        setTimeout(function () { enableSubmit(that); }, 1000);
    });

    // start popover annotations for info boxes
    $('[data-toggle="popover"]').popover({
        html: true,
        placement: 'left',
        trigger: 'hover'
    });
});
