Handlebars.registerHelper('ifEq', function (v1, v2, options) {
    if (v1 === v2) {
        return options.fn(this);
    }
    return options.inverse(this);
});

const template_entry = Handlebars.compile($('#template_entry').html(), { strict: true });
const template_container = Handlebars.compile($('#template_container').html(), { strict: true });
const template_no_element = Handlebars.compile($('#template_no_element').html(), { strict: true });

/**
 * Creates a program entry in a container.
 * @param {HTMLElement} container The container where the template is rendered into.
 * @param {String} type Specifies the type of the entry.
 * @param {Function} query_slaves A function which returns a Promise which queries a query set.
 * @param {Function} query_type A function which is called every time the choice changes.
 */
const addTypeEntry = function (container, type, query_slaves, query_type, context) {
    query_slaves().then(function (slaves) {
        $(container).find('.slave-no-elements').remove();
        let entry_container = $(container).find('.script-' + type + '-content').first();

        if (slaves.length === 0) {
            let html = template_no_element({ type });
            entry_container.append(html);
        } else {
            let template_context = Object.assign({}, { 'slaves': slaves, 'type': type }, context);

            let html = template_entry(template_context);

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

            box.find('.script-' + type + '-slave').trigger('change');
        }
    });
}

var JsonForm = {
    init(container, options) {
        $('.script-program-add').on('click', function () {
            addTypeEntry(container, 'program', options.query_slaves_programs, options.query_programs);
        });

        $('.script-file-add').on('click', function () {
            addTypeEntry(container, 'file', options.query_slaves_files, options.query_files);
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

        json.programs.forEach(function (idx, val) {
            addTypeEntry(container, 'program', options.query_slaves_programs, options.query_programs, { 'choices_current': val.slave, 'selects': [val.program] })
        });

        json.files.forEach(function (idx, val) {
            addTypeEntry(container, 'file', options.query_slaves_files, options.query_files, { 'choices_current': val.slave, 'selects': [val.file] })
        });
    },
    /**
     * Tries to get the current modification and returns it as an JSON object.
     * @param {HTMLElement} container
     * @returns JSON Objects
     */
    dumps(container) {
        json = new Object();

        json.name = $(container).find('.script-name').first().val();

        if (json.name === null) {
            return;
        }

        let dumps_array = function (type) {
            let output = [];

            $(container).find('.script-' + type + '-content').first().find('.script-' + type + '-entry').each(function (idx, val_raw) {

                let entry = new Object();
                let val = $(val_raw);

                entry.index = Number(val.find('.script-' + type + '-index').first().val());
                entry[type] = val.find('.script-' + type + '-program').first().val();
                entry.slave = val.find('.script-' + type + '-slave').first().val();

                let error = false;

                if (entry.slave === '' || entry.slave === null) {
                    error = true;
                } else if (entry[type] === '' || entry[type] === null) {
                    error = true;
                }

                if (entry.index === null) {
                    error = true;
                }

                if (entry) {
                    output.forEach(function (element) {
                        if (element[type] == entry[type] && element.slave == entry.slave) {
                            error = true;
                            console.log("Double entry");
                        }
                    });
                }

                if (!error) {
                    output.push(entry);
                }
            });

            return output;
        };

        json.programs = dumps_array('program');
        json.files = dumps_array('file');

        if (json.programs.length === 0 && json.files.length === 0) {
            return null;
        } else {
            return json;
        }
    }
};
