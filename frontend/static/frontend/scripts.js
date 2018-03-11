/* eslint-env browser */
/* eslint no-use-before-define: ["error", { "functions": false }] */
/* global $, JsonForm, modalDeleteAction, notify, basicRequest, Promise */
/* exported loadScript, newScript, unloadWarning */

// global variable, which indicates whether
// an unload warning should be triggered
var unloadWarning = false;

function promiseQuery(url) {
    return new Promise(function (resolve, reject) {
        basicRequest({
            type: 'GET',
            url: url,
            action: 'query',
            onSuccess(payload) {
                resolve(payload);
            },
            onError(payload) {
                notify('Autocomplete query', 'Error while querying for autocomplete: ' + JSON.stringify(payload));
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
        return promiseQuery('/api/programs?is_string=true&slave=' + slave);
    },
    querySlavesFiles() {
        return promiseQuery('/api/slaves?filesystems=True');
    },
    queryFilesystems(slave) {
        return promiseQuery('/api/filesystems?is_string=true&slave=' + slave);
    },
};

var createEditor = function (json, id) {
    let container = document.getElementById('jsoneditor_' + id);
    JsonForm.loads(container, options, json);
};

function loadScript(id) {
    basicRequest({
        type: 'GET',
        url: '/api/script/' + id + '?programs=str&filesystems=str&slaves=str',
        action: 'loading script',
        onSuccess(payload) {
            createEditor(payload, id);
        },
        onError(payload) {
            notify('Loading script', 'Error while loading script: ' + JSON.stringify(payload));
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
    // Restores the last clicked script
    (function () {
        let href = localStorage.getItem('status_script');
        if (href !== null) {
            let iter = $('.script-tab-link').filter(function (idx, val) {
                return val.hasAttribute('href') && val.getAttribute('href') === href;
            });

            iter.click();
        }
    }());

    // Set color of the current selected.
    $('.script-tab-link.active').addClass('border-dark bg-dark text-light')
        .children('span').addClass('text-dark')    ;

    // Changes the color of the clicked slave, if it was not clicked before.
    $('.script-tab-link').click(function () {
        if (!$(this).hasClass('active')) {
            // Remove color from the old tabs
            $('.script-tab-link').each(function (idx, val) {
                $(val).removeClass('border-dark bg-dark text-light')
                    .addClass('text-dark')
                    .children('span').removeClass('text-dark');
            });
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

            // Save Class when opening for every Slave
            localStorage.setItem('status_script', $(this).attr('href'));

            // Change the color of the current tab
            $(this).removeClass('text-dark')
                .addClass('border-dark bg-dark text-light')
                .children('span').addClass('text-dark');
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

        basicRequest({
            url: '/api/script/' + id + '/copy',
            type: 'POST',
            action: 'copy script',
            onSuccess: function() {
                window.location.reload();
            }
        });
    });

    $('.script-action-add-save').click(function () {
        window.unloadWarning = false;

        let id = $(this).attr('data-editor-id');
        let editor = JsonForm.dumps($('#jsoneditor_' + id));
        let string = JSON.stringify(editor);

        basicRequest({
            type: 'POST',
            url: '/api/scripts',
            action: 'adding new script',
            data: string,
            onSuccess() {
                window.location.reload();
            },
        });
    });

    $('.script-action-save').click(function () {
        window.unloadWarning = false;
        let id = $(this).attr('data-editor-id');
        let editor = JsonForm.dumps($('#jsoneditor_' + id));
        let string = JSON.stringify(editor);

        basicRequest({
            type: 'PUT',
            url: '/api/script/' + id,
            action: 'saving changes for script',
            data: string,
            onSuccess() {
                window.location.reload();
            },
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

    $('.delete-btn').click(function () {
        $('.script-tab-link').first().click();
    });

    $('.unload-warning').click(function() {
        unloadWarning = true;
    });

    $('.form-control[required]').keyup(function () {
        $('.script-action-add-save').prop('disabled', this.value === '' ? true : false);
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
