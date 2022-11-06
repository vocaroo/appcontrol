const path = require("path");
const fs = require("fs-extra");
const constants = require("./constants.js");
const {validateAppName} = require("./validateConfig.js");

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
	return path.join(process.env.HOME, ".ssh/id_ed25519");
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
