socket = new WebSocket('ws://' + window.location.host + '/notifications');
socket.onmessage = function (data) {
	let status = Status.from_json(data.data);

    console.log(status)
	if(status.payload['slave_status'] != null) {
        // handle slave status updates

        let statusButton = $('#slaveStatus_' + status.payload['sid']);
        switch (status.payload['slave_status']) {
            case 'connected':
                console.log(status.payload['sid'] + ' has connected');

                statusButton.removeClass('btn-danger');
                statusButton.addClass('btn-success');
                break;
            case 'disconnected':
                console.log(status.payload['sid'] + ' has disconnected');

                statusButton.removeClass('btn-success');
                statusButton.addClass('btn-danger');
                break;
        }
    } else if(status.payload['program_status'] != null) {
        // handle program status updates

        let statusButton = $('#programStatus_' + status.payload['pid']);
        switch (status.payload['program_status']) {
            case 'started':
                console.log(status.payload['pid'] + ' has started');

                statusButton.removeClass('btn-danger');
                statusButton.addClass('btn-success');
                statusButton.prop('title', 'Running');
                statusButton.attr('data-original-title', 'Running');
                break;
            case 'finished':
                console.log(status.payload['pid'] + ' has finished with Code ' + status.payload['code']);

                statusButton.removeClass('btn-success');
                statusButton.addClass('btn-danger');

                let new_title = 'Stopped with Code ' + status.payload['code'];
                statusButton.prop('title', new_title);
                statusButton.attr('data-original-title', new_title)
                break;
        }
    } else {
        console.log("unknown");
	    console.log(status.payload);
        $.notify({
            type: 'warning',
            message: 'received unknown response from server'
        });
    }
};
socket.onopen = function () {
	console.log('Websocket opened')
};
// Call onopen directly if socket is already open
if (socket.readyState === WebSocket.OPEN) socket.onopen();
