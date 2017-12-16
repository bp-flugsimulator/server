class Status {
	constructor (status, payload) {
		if (status !== "ok" && status !== "err") {
			throw new TypeError("Status only accept a string with `ok` or `err`..");
		} else {
			this._status = status;
			this._payload = payload;
		}
	}

	equals(other) {
		return this.status === other.status &&
			this.payload === other.payload;
	}

	get status() {
		return this._status;
	}

	get payload() {
		return this._payload;
	}

	is_ok() {
		return this.status === "ok";
	}

	is_err() {
		return this.status === "err";
	}

	static ok(payload) {
		return new Status("ok", payload);
	}

	static err(payload) {
		return new Status("err", payload);
	}

	to_json() {
		return JSON.stringify({ "status": this.status, "payload": this.payload });
	}

	static from_json(data) {
		var json = JSON.parse(data);
		return new Status(json["status"], json["payload"]);
	}
}
