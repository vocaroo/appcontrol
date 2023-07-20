
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

class RemoteScriptFailedError extends Error {
	constructor(scriptName, host, code) {
		super(`Remote script ${scriptName} on server ${host} failed, exit code ${code}`);
		this.name = "RemoteScriptFailedError";
		this.scriptName = scriptName;
		this.host = host;
		this.exitCode = code;
	}
}

module.exports = {
	HostVerificationError,
	ServerNotDefinedError,
	RemoteScriptFailedError
};
