const path = require("path");
const fs = require("fs-extra");
const constants = require("./constants.js");

// Read json sync, returning empty object {} if no file existed
// Also return {} if an empty file
function readJson(filePath) {
	let json = {};
	
	try {		
		if (fs.statSync(filePath).size == 0) {
			return {};
		}
		
		json = fs.readJsonSync(filePath);
	} catch (error) {
		if (error.code != "ENOENT") {
			throw error;
		}
	}
	
	return json;
}

// lower case and replace any spaces with a hyphen
function validateAppName(name) {
	return name.trim().toLowerCase().replace(/\s+/g, "-");
}

function appNameFromDir(dirPath) {
	return validateAppName(path.basename(dirPath));
}

function findProjectName() {
	// use same format as an app name
	return appNameFromDir(process.cwd());
}

function getReleaseDir(releaseNumber) {
	return constants.RELEASE_DIR + `/release-${releaseNumber}`;
}

// Could check config for a ssh key path too, before falling back to .ssh dir
// should probably throw an error if none exist
function getSSHKeyPath() {
	return path.join(process.env.HOME, ".ssh/id_rsa");
}

// a key used by control server to access other servers
// unique for each deploy target
function getControlKeyPath(target) {
	return constants.CONTROL_KEY_DIR + "/" + target;
}

module.exports = {
	readJson,
	validateAppName,
	appNameFromDir,
	findProjectName,
	getReleaseDir,
	getSSHKeyPath,
	getControlKeyPath
};
