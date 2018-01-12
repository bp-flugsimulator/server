/* eslint-env browser */
/* global $, jQuery, Status */
/* exported  getCookie, modalDeleteAction, handleFormStatus, clearErrorMessages */

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
                $.notify({
                    message: JSON.stringify(status.payload)
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
}

/**
 * Handles the incoming status from a form request. The page will be reloaded or
 * the errors will be marked in the input field.
 *
 * @param {HTMLElement} form
 * @param {Status} status
 *
 */
function handleFormStatus(form, status) {
    if (status.is_ok()) {
        window.location.reload();
    } else {
        clearErrorMessages(form);

        // insert new feedback
        $.each(status.payload, function (id, msg) {
            let node = form.find('input[name=' + id + ']');
            node.addClass('is-invalid');
            node.parent().append('<div class="invalid-feedback">' + msg + '</div>');
        });
    }
}

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
