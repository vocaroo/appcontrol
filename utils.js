const path = require("path");
const fs = require("fs-extra");
const constants = require("./constants.js");
const {validateAppName} = require("./validateConfig.js");

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

function readLocalConfig() {
	return readJson(constants.LOCAL_CONFIG_FILE);
}

function appNameFromDir(dirPath) {
	return validateAppName(path.basename(dirPath));
}

function findProjectName() {
	let config = readLocalConfig();
	
	if (config.name) {
		return validateAppName(config.name);
	}
	
	// By default, name the project after its directory
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

function hostToProp(host) { // turn an IP address into a string that can be used as a lowdb object property
	return host.replace(/\./g, "-").replace(/:/g, "_");
}

module.exports = {
	readJson,
	validateAppName,
	appNameFromDir,
	readLocalConfig,
	findProjectName,
	getReleaseDir,
	getSSHKeyPath,
	getControlKeyPath,
	hostToProp
};
