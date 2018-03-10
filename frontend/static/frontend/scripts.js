/* eslint-env browser */
/* eslint no-use-before-define: ["error", { "functions": false }] */
/* global $, JsonForm, getCookie, Status, modalDeleteAction, notify, basicRequest, Promise */
/* exported loadScript, newScript, unloadWarning */

// global variable, which indicates whether
// an unload warning should be triggered
var unloadWarning = false;

function promiseQuery(url) {
    return new Promise(function (resolve, reject) {
        $.ajax({
            url,
            beforeSend(xhr) {
                xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
            },
            converters: {
                'text json': Status.from_json
            },
            success(status) {
                if (status.is_ok()) {
                    resolve(status.payload);
                } else {
                    notify('Autocomplete query', 'Error while querying for autocomplete: ' + JSON.stringify(status.payload));
                    reject();
                }
            },
            error(xhr, errorString, errorCode) {
                notify('Autocomplete query', 'Error while querying for autocomplete: ' + errorCode + '(' + errorString + ')');
                reject();
            }
        });
    });
}

const options = {
    querySlavesPrograms() {
        return promiseQuery('/api/slaves?programs=True');
    },
    queryPrograms(slave) {
        return promiseQuery('/api/programs?slave_str=true&slave=' + slave);
    },
    querySlavesFiles() {
        return promiseQuery('/api/slaves?filesystems=True');
    },
    queryFilesystems(slave) {
        return promiseQuery('/api/filesystems?slave_str=true&slave=' + slave);
    },
};

var createEditor = function (json, id) {
    let container = document.getElementById('jsoneditor_' + id);
    JsonForm.loads(container, options, json);
};

function loadScript(id) {
    $.ajax({
        url: '/api/script/' + id + '?programs=str&filesystems=str&slaves=str',
        beforeSend(xhr) {
            xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
        },
        converters: {
            'text json': Status.from_json
        },
        success(status) {
            if (status.is_ok()) {
                createEditor(status.payload, id);
            } else {
                notify('Loading script', 'Error while loading script: ' + JSON.stringify(status.payload));
            }
        },
        error(xhr, errorString, errorCode) {
            notify('Loading script', 'Error while loading script: ' + errorCode + '(' + errorString + ')');
        }
    });
}

function newScript(name) {
    let defaultJson = {
        name,
        programs: [],
        filesystems: [],
    };

    createEditor(defaultJson, name);
}

$(document).ready(function () {
    // Set color of the current selected.
    $('.script-tab-link.active').parent('li').css('background-color', '#dbdbdc');

    // Changes the color of the clicked slave, if it was not clicked before.
    $('.script-tab-link').click(function () {
        if (!$(this).hasClass('active')) {
            // Remove color from the old tabs
            $('.active').removeClass('active');
            // Create a change listener on all available input fields
            $(':input').on('input', function() {
                unloadWarning = true;
                removeAllChangeListener();
            });

            $('select').on('input', function() {
                unloadWarning = true;
                removeAllChangeListener();
            });

            $('.inline-add-button').on('click', function() {
                unloadWarning = true;
            });

            // Change the color of the current tab
            $(this).parent('li').addClass('active');
        }
    });

    $('#deleteScriptModalButton').click(function () {
        modalDeleteAction($('#scriptFrom'), 'script');
    });

    $('.script-action-add').click(function () {
        $('#scriptTabNew').click();
    });

    $('.script-action-copy').click(function () {
        let id = $(this).attr('data-script-id');
        basicRequest('/api/script/' + id + '/copy', 'GET', 'copy script', {} ,() => {window.location.reload();});
    });

    $('.script-action-add-save').click(function () {
        window.unloadWarning = false;

        let id = $(this).attr('data-editor-id');
        let editor = JsonForm.dumps($('#jsoneditor_' + id));
        let string = JSON.stringify(editor);

        $.ajax({
            method: 'POST',
            url: '/api/scripts',
            contentType: 'application/json',
            data: string,
            beforeSend(xhr) {
                xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
            },
            converters: {
                'text json': Status.from_json
            },
            success(status) {
                if (status.is_err()) {
                    notify('Could not save script', JSON.stringify(status.payload), 'danger');
                } else {
                    window.location.reload();
                }
            },
            error(xhr, errorString, errorCode) {
                notify('Connection error', 'Could not deliver script add request. (' + errorCode + ')', 'danger');
            }
        });
    });

    $('.script-action-save').click(function () {
        window.unloadWarning = false;
        let id = $(this).attr('data-editor-id');
        let editor = JsonForm.dumps($('#jsoneditor_' + id));
        let string = JSON.stringify(editor);

        $.ajax({
            method: 'PUT',
            url: '/api/script/' + id,
            contentType: 'application/json',
            data: string,
            beforeSend(xhr) {
                xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
            },
            converters: {
                'text json': Status.from_json
            },
            success(status) {
                if (status.is_err()) {
                    notify('Could not save script', JSON.stringify(status.payload), 'danger');
                } else {
                    window.location.reload();
                }
            },
            error(xhr, errorString, errorCode) {
                notify('Connection error', 'Could not deliver script add request. (' + errorCode + ')', 'danger');
            }
        });
    });

    $('.script-action-delete').click(function () {
        let id = $(this).data('script-id');
        let name = $(this).data('script-name');
        let message = '<a>Are you sure you want to remove script </a><b>' + name + '</b>?</a>';

        //changing button visibility and message of the delete modal
        let deleteWarning = $('#deleteWarning');
        deleteWarning.children().find('.modal-body').empty(message);
        deleteWarning.children().find('.modal-body').append(message);

        //adding id to modal and set it visible
        deleteWarning.data('sqlId', id);
        deleteWarning.modal('toggle');
    });

    $('.inline-add-button').on('click', function() {
        unloadWarning = true;
    });
});


$(window).on('beforeunload', function (e) {
    if (this.unloadWarning) {
        let returnText = 'Are you sure you want to leave?';
        e.returnValue = returnText;
        return returnText;
    }
});

function removeAllChangeListener(){
    $(':input').off('input');
    $('select').off('input');
}
