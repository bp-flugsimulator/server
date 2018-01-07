var schema = {
    "title": "Script",
    "type": "object",
    "definitions": {
        "program_entry": {
            "type": "object",
            "properties": {
                "index": {
                    "type": "integer"
                },
                "slave": {
                    "type": ["integer", "string"],
                },
                "program": {
                    "type": ["integer", "string"],
                }
            },
            "required": ["index", "slave", "program"]
        },
        "file_entry": {
            "type": "object",
            "properties": {
                "index": {
                    "type": "integer"
                },
                "slave": {
                    "type": ["integer", "string"],
                },
                "file": {
                    "type": ["integer", "string"],
                }
            },
            "required": ["index", "slave", "file"]
        }
    },
    "properties": {
        "name": {
            "type": "string",
        },
        "programs": {
            "type": "array",
            "items": {
                "$ref": "#/definitions/program_entry"
            }
        },
        "files": {
            "type": "array",
            "items": {
                "$ref": "#/definitions/file_entry"
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
    schema: schema,
    autocomplete: {
        caseSensitive: false,
        //getOptions(text: string, path: string[], input: string, editor: JSONEditor)
        getOptions: function (text, path, input, editor) {
            return new Promise(function (resolve, reject) {
                console.log(text);
                console.log(path);
                console.log(input);
                if (text.length > 2) {
                    console.log("Searching " + text);
                    switch (path[path.length - 1]) {
                        case 'slave':
                        case 'program':
                        case 'file':
                            console.log("Sending");
                            $.ajax({
                                url: "/api/" + path[path.length - 1] + "s?q=" + text,
                                beforeSend: function (xhr) {
                                    xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
                                },
                                converters: {
                                    'text json': Status.from_json
                                },
                                success: function (status) {
                                    if (status.is_ok()) {
                                        console.log("Found");
                                        console.log(status.payload);
                                        resolve(status.payload);
                                    } else {
                                        console.log("Error while querying ");
                                        console.log(status.payload);
                                        reject();
                                    }
                                },
                                error: function (error) {
                                    console.log("Error while querying " + error);
                                    reject();
                                }
                            });
                            break;
                        default:
                            reject();
                            break;
                    }
                } else {
                    reject();
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
                return true
        }
    }
};
// create the editor
var container = document.getElementById('jsoneditor');
var editor = new JSONEditor(container, options, default_json);
editor.expandAll();
