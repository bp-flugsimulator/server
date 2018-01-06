socket = new WebSocket('ws://' + window.location.host + '/notifications');
socket.onmessage = function (data) {
	let status = Status.from_json(data.data);

	// handle slave status updates
	if(status.payload['slave_status'] !== null){

        let statusButton = $('#slaveStatus_' + status.payload['sid']);
        let startstopButton = $('#slaveStartStop_' + status.payload['sid']);
        switch(status.payload['slave_status']) {
            case 'connected':
                console.log(status.payload['sid'] + ' has connected');

                // swap status
                statusButton.removeClass('btn-danger');
                statusButton.addClass('btn-success');

                // swap start and stop functions
                startstopButton.removeClass('start-slave');
                startstopButton.addClass('stop-slave');

                // set tooltip to Stop
                startstopButton.prop('title', 'Stop');
                startstopButton.attr('data-original-title', 'Stop');

                break;
            case 'disconnected':
                console.log(status.payload['sid'] + ' has disconnected');

                // swap status
                statusButton.removeClass('btn-success');
                statusButton.addClass('btn-danger');

                // swap start and stop functions
                startstopButton.removeClass('stop-slave');
                startstopButton.addClass('start-slave');

                // set tooltip to Start
                startstopButton.prop('title', 'Start');
                startstopButton.attr('data-original-title', 'Start');

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
