socket = new WebSocket('ws://' + window.location.host + '/notifications');
socket.onmessage = function (data) {
	let status = Status.from_json(data.data);

	// handle slave status updates
	if(status.payload['slave_status'] !== null){

        let statusButton = $('#slaveStatus_' + status.payload['sid']);
        switch(status.payload['slave_status']) {
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
    } else {
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
