/* eslint-env browser */
/* global $, JSONEditor, getCookie, Status, modalDeleteAction, notify */
/* exported loadScript, newScript */

var schema = {
    'title': 'Script',
    'type': 'object',
    'definitions': {
        'program_entry': {
            'type': 'object',
            'properties': {
                'index': {
                    'type': 'integer',
                    // 'required': true
                },
                'slave': {
                    'type': ['integer', 'string'],
                    // 'required': true
                },
                'program': {
                    'type': ['integer', 'string'],
                    // 'required': true
                }
            },
            'required': ['index', 'slave', 'program'],
            'additionalProperties': false
        },
        'file_entry': {
            'type': 'object',
            'properties': {
                'index': {
                    'type': 'integer',
                    // 'required': true
                },
                'slave': {
                    'type': ['integer', 'string'],
                    // 'required': true
                },
                'file': {
                    'type': ['integer', 'string'],
                    // 'required': true
                }
            },
            'required': ['index', 'slave', 'file'],
            'additionalProperties': false
        }
    },
    'properties': {
        'name': {
            'type': 'string',
        },
        'programs': {
            'type': 'array',
            'items': {
                '$ref': '#/definitions/program_entry'
            },
            'uniqueItems': true
        },
        'files': {
            'type': 'array',
            'items': {
                '$ref': '#/definitions/file_entry'
            },
            'uniqueItems': true
        }
    },
    'required': ['name', 'programs', 'files'],
    'additionalProperties': false
};

function promise_query(url) {
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
                    console.log("Failed 4");
                    reject();
                }
            },
            error(xhr, errorString, errorCode) {
                console.log("Failed 3");
                reject();
            }
        });
    });
}

var options = {
    query_slaves() {
        console.log("query for slaves");
        promise_query('/api/slaves?programs=True');
    },
    query_programs(slave) {
        promise_query('/api/programs?slave_str=true&slave=' + slave);
    },
};

var createEditor = function (json, id) {
    let container = document.getElementById('jsoneditor_' + id);
    JsonForm.loads(container, options, json);
};

var loadScript = function (id) {
    $.ajax({
        url: '/api/script/' + id + '?programs=str&files=str&slaves=str',
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
                console.log("Failed 1");
            }
        },
        error(xhr, errorString, errorCode) {
            console.log("Failed 2");
        }
    });
};

var newScript = function (name) {
    let defaultJson = {
        name,
        programs: [],
        files: [],
    };

    createEditor(defaultJson, name);
};

$(document).ready(function () {
    // Set color of the current selected.
    $('.script-tab-link.active').parent('li').css('background-color', '#dbdbdc');

    // Changes the color of the clicked slave, if it was not clicked before.
    $('.script-tab-link').click(function () {
        if (!$(this).hasClass('active')) {
            // Remove color from the old tabs
            $('.script-tab-link').each(function (idx, val) {
                $(val).parent('li').css('background-color', 'transparent');
            });

            // Change the color of the current tab
            $(this).parent('li').css('background-color', '#dbdbdc');
        }
    });

    $('#deleteScriptModalButton').click(function () {
        modalDeleteAction($('#scriptFrom'), 'script');
    });

    $('.script-action-add').click(function () {
        $('#scriptTabNew').click();
    });

    $('.script-action-add-save').click(function () {
        let id = $(this).attr('data-editor-id');
        let editor = editors['jsoneditor_' + id];
        let string = JSON.stringify(editor.get());

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
        alert('unimplemented');
    });

    $('.script-action-delete').click(function () {
        let id = $(this).data('script-id');
        let name = $(this).data('script-name');
        let message = '<a>Are you sure you want to remove script </a><b>' + name + '</b>?</a>';

        //
        //changing button visibility and message of the delete modal
        let deleteWarning = $('#deleteWarning');
        deleteWarning.children().find('.modal-body').empty(message);
        deleteWarning.children().find('.modal-body').append(message);


        //adding id to modal and set it visible
        deleteWarning.data('sqlId', id);
        deleteWarning.modal('toggle');
    });
});
