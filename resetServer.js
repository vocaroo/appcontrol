const {globalDB, localDB} = require("./db.js");

module.exports = async function(serverId) {
	// Clear any global record of this host being initialised as a control server, so it will be re-initialised
	let controlServerInitStatus = globalDB.get(`controlServerInitStatus`).value();
	
	if (controlServerInitStatus && serverId in controlServerInitStatus) {
		globalDB.set(`controlServerInitStatus.${serverId}`, false)
			.write();
	}
	
	// Clear per-project record of the deployment control key being copied to this host, so will be re-copied
	let controlKeyCopiedStatus = localDB.get(`controlKeyCopiedStatus`).value();
	
	if (controlKeyCopiedStatus) {
		for (const [target, serverIds] of Object.entries(controlKeyCopiedStatus)) {
			if (serverId in serverIds) {
				localDB.set(`controlKeyCopiedStatus.${target}.${serverId}`, false)
					.write();
			}
		}
	}
}
