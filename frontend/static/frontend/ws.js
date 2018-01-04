socket = new WebSocket("ws://" + window.location.host + "/notifications");
socket.onmessage = function (e) {
	console.log(e);
	let data = JSON.parse(e.data);
	$.notify({
		message: data.message
	});
};
socket.onopen = function () {
	console.log('Websocket opened')
};
// Call onopen directly if socket is already open
if (socket.readyState === WebSocket.OPEN) socket.onopen();
