/* eslint-env browser */
/* global $, JSONEditor, getCookie, Status, modalDeleteAction */
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

var options = {
    search: false,
    navigationBar: false,
    modes: ['tree'],
    onError() {
        console.log("error");
    },
    templates: [{
        text: 'File',
        title: 'Insert a File Node',
        className: 'jsoneditor-type-object',
        field: 'FileTemplate',
        value: {
            'index': 0,
            'slave': '',
            'file': ''
        }
    }, {
        text: 'Program',
        title: 'Insert a Program Node',
        className: 'jsoneditor-type-object',
        field: 'ProgramTemplate',
        value: {
            'index': 0,
            'slave': '',
            'program': ''
        }
    }],
    schema,
    autocomplete: {
        caseSensitive: false,
        //getOptions(text: string, path: string[], input: string, editor: JSONEditor)
        getOptions(text, path) {
            return new Promise(function (resolve, reject) {
                switch (path[path.length - 1]) {
                    case 'slave':
                    case 'program':
                    case 'file':
                        $.ajax({
                            url: '/api/' + path[path.length - 1] + 's?q=' + text,
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
                                    $.notify({
                                        message: 'Could not load autocomplete query from server (' + status.payload + ')'
                                    }, {
                                            type: 'danger'
                                        });
                                    reject();
                                }
                            },
                            error(xhr, errorString, errorCode) {
                                $.notify({
                                    message: 'Could not load autocomplete query from server (' + errorCode + ')'
                                }, {
                                        type: 'danger'
                                    });
                            }
                        });
                        break;
                    default:
                        reject();
                        break;
                }
            });
        }
    },
    onEditable(node) {
        switch (node.field) {
            case 'name':
                return {
                    field: false,
                    value: true
                };
            case 'programs':
                return {
                    field: false,
                    value: true
                };
            case 'files':
                return {
                    field: false,
                    value: true
                };
            default:
                return true;
        }
    }
};

var editors = {};

var createEditor = function (json, id) {
    let container = document.getElementById('jsoneditor_' + id);
    let editor = new JSONEditor(container, options, json);
    editors['jsoneditor_' + id] = editor;
    editor.expandAll();
}


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
                $.notify({
                    message: 'Could not load script from server (' + status.payload + ')'
                }, {
                        type: 'danger'
                    });
            }
        },
        error(xhr, errorString, errorCode) {
            $.notify({
                message: 'Could not load script from server (' + errorCode + ')'
            }, {
                    type: 'danger'
                });
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
