
$(document).ready(function () {
    // set defaults for notifications
    $.notifyDefaults({
        type: 'success',
        placement: {
            from: 'bottom',
            align: 'right'
        },
        animate: {
            enter: 'animated fadeInRight',
            exit: 'animated fadeOutRight'
        }
    });

    // Enable tool tips.
    $(function () {
        $("[data-toggle='tooltip']").tooltip()
    });

    /*function for deleting a slave, it is added to the delete_slave button*/
    $('.delete_script').click(function () {
        //get id and name of the slave and create deletion message
        let id = $(this).parents('.script-card').attr('id');
        let name = $(this).parents('.script-card').children().find('.script-name').text();

        console.log(id);
        console.log(name);

        let message = '<a>Are you sure you want to remove script </a><b>' + name + '</b>?</a>';

        //changing button visibility and message of the delete modal
        let deleteWarning = $('#deleteWarning');
        deleteWarning.children().find('.modal-body').empty(message);
        deleteWarning.children().find('.modal-body').append(message);

        //adding id to modal and set it visible
        deleteWarning.data('sqlId', id);
        deleteWarning.modal('toggle');
    });

    $('#deleteScriptModalButton').click(function () {
        modalDeleteAction($('#scriptFrom'), 'script')
    });
});
