const {globalDB, localDB} = require("./db.js");
const getFingerprint = require("./getFingerprint.js");
const {getServerDefinition, getServerGroup, hostFromServer, updateKnownHostsForServer} = require("./utils.js");

module.exports = async function(serverKey) {
	const serverDef = getServerDefinition(serverKey);
	const serverId = serverDef.uniqueId;
	const serverGroup = getServerGroup(serverKey);
	
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
	
	// Get a new fingerprint
		
	console.log("Getting server fingerprint...");
	
	let fingerprint = await getFingerprint(hostFromServer(serverDef));
	
	// Update global server definition
	
	globalDB.get(`servers.${serverGroup}`)
		.find({uniqueId : serverId})
		.assign({fingerprint : fingerprint})
		.write();
		
	console.log("Updating known_hosts");
	
	// update with *new* fingerprint
	updateKnownHostsForServer(serverDef, fingerprint);
	
	console.log("Done resetting server.");
}
