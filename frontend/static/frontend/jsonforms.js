Handlebars.registerHelper('ifEq', function (v1, v2, options) {
    if (v1 === v2) {
        return options.fn(this);
    }
    return options.inverse(this);
});

const template_entry = Handlebars.compile($('#template_entry').html(), { strict: true });
const template_container = Handlebars.compile($('#template_container').html(), { strict: true });

/**
 * Creates a program entry in a container.
 * @param {HTMLElement} container The container where the template is rendered into.
 * @param {String} type Specifies the type of the entry.
 * @param {Function} query_slaves A function which returns a Promise which queries a query set.
 * @param {Function} query_type A function which is called every time the choice changes.
 */
const addTypeEntry = function (container, type, query_slaves, query_type, context) {
    query_slaves().then(function (slaves) {
        console.log(slaves);
        let template_context = Object.assign({}, { 'slaves': slaves, 'type': type }, context);

        console.log("Pre-Template");

        let html = template_entry(template_context);

        console.log("Post-Template");

        let entry_container = $(container).find('.script-' + type + '-content').first();

        entry_container.append(html);

        let box = entry_container.children().last();

        box.find('.script-' + type + '-remove').on('click', function () {
            box.remove();
        });

        box.find('.script-' + type + '-slave').on('change', function () {
            query_type($(this).find('option:selected').first().val()).then(
                function (query) {
                    box.find('.script-' + type + '-program').each(function (idx, val) {
                        let target = $(val);
                        target.children().remove();
                        target.removeAttr('hidden');

                        $(query).each(function (idx, val) {
                            target.append("<option> " + val + " </option>");
                        });
                    });
                }
            );
        });
    });
}

var JsonForm = {
    init(container, options) {
        $('.script-program-add').on('click', function () {
            addProgramEntry(container, options.query_slaves, options.query_programs);
        });

        $('.script-file-add').on('click', function () {

        });
    },
    /**
     * Creates a form from a JSON object.
     * @param {HTMLElement} container
     * @param {JSONObject} json
     */
    loads(container, options, json) {
        $(container).append(template_container({ 'name': json.name }));
        this.init(container, options);

        $(json.programs).each(function (idx, val) {
            addTypeEntry(container, 'program', options.query_slaves, options.query_programs, { 'choices_current': val.slave, 'selects': [val.program] })
        });

        $(json.files).each(function (idx, val) {
            addTypeEntry(container, 'file', options.query_slaves, options.query_files, { 'choices_current': val.slave, 'selects': [val.file] })
        });
    },
    /**
     * Tries to get the current modification and returns it as an JSON object.
     * @param {HTMLElement} container
     * @returns JSON Objects
     */
    dumps(container) {
        json = new Object();

        json['script_name'] = $(container).find('script-name').first().value();

        var dumps_array = function (type) {
            let output = [];

            $(container).find('script-program-content').first().find('.script-program-entry').each(function (idx, val) {
                let entry = new Object();

                entry['index'] = val.find('.script-program-index').first();
                entry[type] = val.find('.script-program-program').first();
                entry['slave'] = val.find('.script-program-slave').first();

                let error = false;

                if (entry['slave'] === '' || entry['slave'] === null) {
                    error = true;
                } else if (entry[type] === '' || entry[type] === null) {
                    error = true;
                }

                if (entry['index'] === '' || entry['index'] === null) {
                    error = true;
                }
                innerHTML
                if (!error) {
                    output.push(entry);
                }
            });

            return output;
        };

        json['programs'] = dumps_array('programs');
        json['files'] = dumps_array('files');
    }
};
