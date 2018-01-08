/**
 * Get a cookie by it the name. If the cookie is not present 'null' will be
 * returned.
 * @param {string} name Cookie name
 */
function getCookie(name) {
    if (document.cookie && document.cookie !== '') {
        let cookie = document.cookie.split(',').find(function (raw_cookie) {
            let cookie = jQuery.trim(raw_cookie);
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
function clearErrorMessages(form) {
    form.find("div[class='invalid-feedback']").each(function (index, item) {
        item.remove();
    });

    form.find('.is-invalid').each(function (index, item) {
        $(item).removeClass('is-invalid');
    });
}
