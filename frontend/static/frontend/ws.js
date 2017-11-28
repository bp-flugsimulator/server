socket = new WebSocket("ws://" + window.location.host + "/chat/");
socket.onmessage = function(e) {
	var data = JSON.parse(e.data);
	$.notify({
		message: data.message
	});
}
socket.onopen = function() {
	console.log('Websocket opened')
}
// Call onopen directly if socket is already open
if (socket.readyState == WebSocket.OPEN) socket.onopen();
