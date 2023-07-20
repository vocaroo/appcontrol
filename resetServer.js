const util = require("util");
const child_process = require("child_process");
const path = require("path");
const os = require("os");
const fsp = require("fs").promises;
const {globalDB, localDB} = require("./db.js");
const getFingerprint = require("./getFingerprint.js");
const {getServerDefinition, getServerGroup, hostFromServer} = require("./utils.js");
const exec = util.promisify(child_process.exec);

const knownHostsPath = path.join(os.homedir(), ".ssh/known_hosts");

async function updateKnownHosts(hostIP, fingerprint) {
	await exec(`ssh-keygen -R "${hostIP}"`);
	await fsp.appendFile(knownHostsPath, `${hostIP} ssh-ed25519 ${fingerprint}\n`);
}

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
		
	// Update local user's known_hosts
	
	console.log("Updating known_hosts");
	
	if (serverDef.ipv4) {
		updateKnownHosts(serverDef.ipv4, fingerprint);
	}
	
	if (serverDef.ipv6) {
		updateKnownHosts(serverDef.ipv6, fingerprint);
	}
	
	console.log("Done resetting server.");
}
