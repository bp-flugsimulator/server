var json = {
    name: "Script",
    programs: [],
    files: [],
};

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
                "$ref": "#/definitions/program_entry"
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
var editor = new JSONEditor(container, options, json);
editor.expandAll();
