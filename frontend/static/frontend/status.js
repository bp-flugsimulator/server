class Status {
    constructor (status, payload) {
        if (status !== "ok" && status !== "err") {
            throw new TypeError("Status only accept a string with `ok` or `err`..");
        } else {
            this._status = status;
            this._payload = payload;
            //generate uuid
            let uuid = "", i, random;
            for (i = 0; i < 32; i++) {
                random = Math.random() * 16 | 0;
                if (i === 8 || i === 12 || i === 16 || i === 20) {
                    uuid += "-"
                }
                uuid += (i == 12 ? 4 : (i == 16 ? (random & 3 | 8) : random)).toString(16);
            }
            this._uuid = uuid;
        }
    }

    equals(other) {
        return this.status === other.status &&
            this.payload === other.payload &&
            this.uuid === other.uuid;
    }

    get status() {
        return this._status;
    }

    get payload() {
        return this._payload;
    }

    get uuid(){
        return this._uuid;
    }

    set uuid(id){
        this._uuid = id;
    }

    is_ok() {
        return this.status === 'ok';
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
        return JSON.stringify({ "status": this.status, "payload": this.payload, "uuid": this.uuid });
    }

    static from_json(data) {
        let json = JSON.parse(data);
        let object = new Status(json["status"], json["payload"]);
        object.uuid = json["uuid"];
        return object;
    }
}