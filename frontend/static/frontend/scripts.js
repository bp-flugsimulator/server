/* eslint-env browser */
/* global $, JSONEditor, getCookie, Status */
/* exported loadScript, newScript */

var schema = {
    'title': 'Script',
    'type': 'object',
    'definitions': {
        'program_entry': {
            'type': 'object',
            'properties': {
                'index': {
                    'type': 'integer'
                },
                'slave': {
                    'type': ['integer', 'string'],
                },
                'program': {
                    'type': ['integer', 'string'],
                }
            },
            'required': ['index', 'slave', 'program']
        },
        'file_entry': {
            'type': 'object',
            'properties': {
                'index': {
                    'type': 'integer'
                },
                'slave': {
                    'type': ['integer', 'string'],
                },
                'file': {
                    'type': ['integer', 'string'],
                }
            },
            'required': ['index', 'slave', 'file']
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
            }
        },
        'files': {
            'type': 'array',
            'items': {
                '$ref': '#/definitions/file_entry'
            }
        }
    }
};

var options = {
    search: false,
    navigationBar: false,
    modes: ['tree'],
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
                            error(xhr, error_string, errorCode) {
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
    onEditable: function (node) {
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

var createEditor = function (json, id) {
    let container = document.getElementById('jsoneditor_' + id);
    let editor = new JSONEditor(container, options, json);
    editor.expandAll();
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
                $.notify({
                    message: 'Could not load script from server (' + status.payload + ')'
                }, {
                    type: 'danger'
                });
            }
        },
        error(xhr, error_string, errorCode) {
            $.notify({
                message: 'Could not load script from server (' + errorCode + ')'
            }, {
                type: 'danger'
            });
        }
    });
};

var newScript = function (name) {
    let default_json = {
        name,
        programs: [],
        files: [],
    };

    createEditor(default_json, 'new');
};
