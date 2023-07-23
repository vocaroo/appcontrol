const path = require("path");
const assert = require("assert");
const fs = require("fs-extra");
const util = require("util");
const child_process = require("child_process");
const os = require("os");
const fsp = require("fs").promises;
const constants = require("./constants.js");
const {globalDB} = require("./db.js");
const {ServerNotDefinedError} = require("./errors.js");
const exec = util.promisify(child_process.exec);

// Read json sync, returning empty object {} if no file existed
// Also return {} if an empty file
function readJson(filePath, suppressSyntaxError = false) {
	let json = {};
	
	try {		
		if (fs.statSync(filePath).size == 0) {
			return {};
		}
		
		json = fs.readJsonSync(filePath);
	} catch (error) {
		let ignoreError = error.code == "ENOENT"
			|| (suppressSyntaxError && error instanceof SyntaxError);
		
		if (!ignoreError) {
			throw error;
		}
	}
	
	return json;
}

// lower case and replace any spaces with a hyphen
// used for both app names and also some other things (target name, project name...)
function validateAppName(name) {
	name = name.trim().toLowerCase().replace(/\s+/g, "_");
	assert(/^[a-z][-_a-z0-9]+$/.test(name), `Invalid app name or other name: ${name}`);
	assert(!name.includes("---"), `App name or other name must not contain three hyphens: ${name}`);
	return name;
}

function appNameFromDir(dirPath) {
	return validateAppName(path.basename(dirPath));
}

function getNumberedReleaseDir(releaseDir, releaseNumber) {
	return releaseDir + `/release-${releaseNumber}`;
}

// a key used by control server to access other servers
// unique for each deploy target
function getControlKeyPath(target) {
	return constants.CONTROL_KEY_DIR + "/" + target;
}

// Utility for informational output only
function serverToStr(server) {
	if (server.hostname) {
		return server.hostname;
	}
	
	return hostFromServer(server);
}

function hostFromServer(server) {
	assert(server.ipv6 || server.ipv4);
	
	if (server.ipv6) {
		return server.ipv6;
	} else {
		return server.ipv4;
	}
}

function getGlobalServerDefinitions() {
	const serverGroups = globalDB.get("servers").value();
	
	// Combine all servers from different groups into one list
	if (serverGroups) {
		return Object.values(serverGroups).reduce((accum, value) => accum.concat(value), []);
	}
	
	return [];
}

async function updateKnownHosts(hostIP, fingerprint) {
	await exec(`ssh-keygen -R "${hostIP}"`);
	await fsp.appendFile(constants.KNOWN_HOSTS_PATH, `${hostIP} ssh-ed25519 ${fingerprint}\n`);
}

// If fingerprint is not given, will use the current one from server
// Otherwise, use the specified fingerprint
async function updateKnownHostsForServer(server, fingerprint = null) {
	if (fingerprint == null) {
		fingerprint = server.fingerprint;
	}
	
	if (server.ipv4) {
		await updateKnownHosts(server.ipv4, fingerprint);
	}
	
	if (server.ipv6) {
		await updateKnownHosts(server.ipv6, fingerprint);
	}
}

// Check there are no duplicates in array
function allDifferent(array) {
	return array.length === new Set(array).size;
}

function compareServerToKey(server, serverKey) {
	// Ensure there is nothing stupid like a hostname that contains a wrong IP address, which would match
	assert(allDifferent([server.ipv4, server.ipv6, server.hostname, server.uniqueId]));
	
	return (server.ipv4 === serverKey || server.ipv6 === serverKey || server.hostname === serverKey
			|| server.uniqueId === serverKey);
}

function getServerDefinition(serverKey) {
	const serverInfos = getGlobalServerDefinitions();
	
	if (serverInfos.length > 0) {
		for (let serverInfo of serverInfos) {
			if (compareServerToKey(serverInfo, serverKey)) {
				return serverInfo;
			}
		}
	}
	
	throw new ServerNotDefinedError(serverKey);
}

function getServerGroup(serverKey) {
	const serverGroups = globalDB.get("servers").value();
	
	if (serverGroups) {
		for (const [group, serverInfos] of Object.entries(serverGroups)) {
			for (let serverInfo of serverInfos) {
				if (compareServerToKey(serverInfo, serverKey)) {
					return group;
				}
			}
		}
	}
	
	throw new ServerNotDefinedError(serverKey);
}

module.exports = {
	readJson,
	validateAppName,
	appNameFromDir,
	getNumberedReleaseDir,
	getControlKeyPath,
	serverToStr,
	hostFromServer,
	updateKnownHostsForServer,
	getGlobalServerDefinitions,
	getServerDefinition,
	getServerGroup
};
