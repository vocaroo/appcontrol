const path = require("path");
const assert = require("assert");
const fs = require("fs-extra");
const constants = require("./constants.js");

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

// Could check config for a ssh key path too, before falling back to .ssh dir
// should probably throw an error if none exist
function getSSHKeyPath() {
	return path.join(process.env.HOME, ".ssh/id_ed25519");
}

// a key used by control server to access other servers
// unique for each deploy target
function getControlKeyPath(target) {
	return constants.CONTROL_KEY_DIR + "/" + target;
}

function hostToProp(host) { // turn an IP address into a string that can be used as a lowdb object property
	return host.replace(/\./g, "-").replace(/:/g, "_");
}

module.exports = {
	readJson,
	validateAppName,
	appNameFromDir,
	getNumberedReleaseDir,
	getSSHKeyPath,
	getControlKeyPath,
	hostToProp
};
