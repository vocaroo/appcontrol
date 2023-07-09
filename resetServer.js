const {globalDB, localDB} = require("./db.js");
const {hostToProp} = require("./utils.js");

module.exports = async function(host) {
	// Clear any global record of this host being initialised as a control server, so it will be re-initialised
	let controlServerInitStatus = globalDB.get(`controlServerInitStatus`).value();
	
	if (controlServerInitStatus && hostToProp(host) in controlServerInitStatus) {
		globalDB.set(`controlServerInitStatus.${hostToProp(host)}`, false)
			.write();
	}
	
	// Clear per-project record of the deployment control key being copied to this host, so will be re-copied
	let controlKeyCopiedStatus = localDB.get(`controlKeyCopiedStatus`).value();
	
	if (controlKeyCopiedStatus) {
		for (const [target, hosts] of Object.entries(controlKeyCopiedStatus)) {
			if (hostToProp(host) in hosts) {
				localDB.set(`controlKeyCopiedStatus.${target}.${hostToProp(host)}`, false)
					.write();
			}
		}
	}
}
