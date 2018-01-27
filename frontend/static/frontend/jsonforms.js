Handlebars.registerHelper('ifEq', function (v1, v2, options) {
    if (v1 === v2) {
        return options.fn(this);
    }
    return options.inverse(this);
});

/**
 * Allow context attributes
 * {
 *  type: string, modifies the different class names
 *  type-display: string, modifes the name of the display header
 *  index: integer, modifies the current index.
 *  choices_current: String, modifies the current selected choice for the slaves
 *  choices: Array, modifies the available choices for the slaves
 *  selects: Array, modifies the current selected programs.
 * }
 */
const entry_template = Handlebars.compile(`
<div class="script-{{type}}-entry">
    <button class="script-{{type}}-remove" type="button">X</button>
    <div class="form-group row">
        <label class="col-1">Index</label>
        <input class="form-control col script-{{type}}-index" type="number" value="{{#if index}}{{index}}{{else}}0{{/if}}" />
    </div>

    <div class="form-group row slave-choice">
        <lable class="col-1">Client</lable>
        <select class="form-control col script-{{type}}-slave" type="text">
            {{#each choices}}
            <option {{#ifEq choices_current this}}selected{{/if}}> {{ this }} </option>
            {{/ each}}
          </select>
    </div>

    <div class="form-group row {{type}}-choice" >
        <lable class="col-1">{{#if type-display}}{{type-display}}{{else}}{{type}}{{/if}}</lable>
        <select class="form-control col script-{{type}}-{{type}}" type="text" {{#if selects}}{{else}}hidden{{/if}}>
            {{#each selects}}
            <option> {{ this }} </option>
            {{/ each}}
        </select>
    </div>
</div>
`);

const container_template = Handlebars.compile(`
<div class="form-group row">
    <lable class="col-2">Script Name</lable>
    <input class="form-control col script-name" type="text" value="{{#if name}}{{name}}{{/if}}" />
</div>

<div class="row">
    <div class="col-2">
        <lable>Programs</lable>
        <button type="button" class="script-program-add">+</button>
    </div>

    <div class="script-program-content" class="col">
    </div>
</div>
`);

var JsonForm = {
    /**
     * Creates a form from a JSON object.
     * @param {HTMLElement} container
     * @param {JSONObject} json
     */
    loads(container, json, options) {
        $(container).append(container_template({ 'name': json.name }));

        $(json.programs).each(function (idx, val) {
            addProgramEntry(container, options.query_set, options.callback, { 'choices_current': val.slave, 'selects': [val.program] })
        });
    },
    /**
     * Tries to get the current modification and returns it as an JSON object.
     * @param {HTMLElement} container
     * @returns JSON Objects
     */
    dumps(container) {
        json = new Object();
        json['programs'] = [];

        json['script_name'] = $(container).find('script-name').first().value();

        $(container).find('script-program-content').first().find('.script-program-entry').each(function (idx, val) {
            let entry = new Object();

            entry['index'] = val.find('.script-program-index').first();
            entry['program'] = val.find('.script-program-program').first();
            entry['slave'] = val.find('.script-program-slave').first();

            let error = false;

            if (entry['slave'] === '' || entry['slave'] === null) {
                error = true;
            } else if (entry['program'] === '' || entry['program'] === null) {
                error = true;
            }

            if (entry['index'] === '' || entry['index'] === null) {
                error = true;
            }

            if (!error) {
                json['programs'].push(entry);
            }
        });

        json['slaves'] = [];
    }
};

/**
 * Creates a program entry in a container.
 * @param {HTMLElement} container The container where the template is rendered into.
 * @param {Function} query_set A function which returns a Promise which queries a query set.
 * @param {Function} callback A function which is called every time the choice changes.
 */
function addProgramEntry(container, query_set, callback, context) {
    query_set().then(function (slaves) {
        let html = entry_template(
            Object.assign({}, { 'choices': query_set, 'type': 'program' }, context));

        let entry_container = $(container).find('.script-program-content').first();
        entry_container.append(html);
        let box = entry_container.children().last();

        box.find('.script-program-remove').on('click', function () {
            box.remove();
        });

        box.find('.script-program-slave').on('change', function () {
            callback($(this).find('option:selected').first()).then(
                function (query) {
                    box.find('.script-program-program').each(function (idx, val) {
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
