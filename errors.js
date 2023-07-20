
class HostVerificationError extends Error {
	constructor(message) {
		super(message);
		this.name = "HostVerificationError";
	}
}

class ServerNotDefinedError extends Error {
	constructor(serverKey) {
		super(`Server ${serverKey} not found in global server definitions.`);
		this.name = "ServerNotDefinedError";
	}
}

module.exports = {
	HostVerificationError,
	ServerNotDefinedError
};
