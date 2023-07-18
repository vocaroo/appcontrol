const path = require("path");
const assert = require("assert");
const fs = require("fs-extra");
const constants = require("./constants.js");
const {globalDB} = require("./db.js");

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
	
	if (server.ipv4) {
		return server.ipv4;
	}
	
	if (server.ipv6) {
		return server.ipv6;
	}
	
	return server.uniqueId;
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

function getServerDefinition(serverKey) {
	const serverInfos = getGlobalServerDefinitions();
	
	if (serverInfos.length > 0) {
		for (let serverInfo of serverInfos) {
			if (serverInfo.ipv4 === serverKey || serverInfo.ipv6 === serverKey || serverInfo.hostname === serverKey) {
				return serverInfo;
			}
		}
	}
	
	return null;
}

module.exports = {
	readJson,
	validateAppName,
	appNameFromDir,
	getNumberedReleaseDir,
	getControlKeyPath,
	serverToStr,
	hostFromServer,
	getServerDefinition
};
