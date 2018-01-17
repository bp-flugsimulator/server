
$(document).ready(function () {
    $('#scriptRun').click(function (event) {
        event.preventDefault();
        let id = $('#scriptSelect :selected').val();

        if (id == null) {
            notify('No script selected.', 'You have to select a script first', 'danger');
        } else {
            $.ajax({
                type: 'GET',
                url: '/api/script/' + id + '/run',
                beforeSend(xhr) {
                    xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
                },
                converters: {
                    'text json': Status.from_json
                },
                success(status) {
                    if (status.is_ok()) {
                        notify('Got result', JSON.stringify(status.payload), 'success');
                    } else {
                        notify('Error', JSON.stringify(status.payload), 'danger');
                    }
                },
                error(xhr, errorString, errorCode) {
                    notify('Error while transport', errorCode, 'danger');
                }
            });
        }
    });
});
