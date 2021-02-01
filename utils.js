const path = require("path");
const fs = require("fs-extra");
const constants = require("./constants.js");

let config = {};

try {
	config = fs.readJsonSync(constants.LOCAL_CONFIG_FILE);
} catch (error) {
	if (error.code != "ENOENT") {
		throw error;
	}
}

// lower case and replace any spaces with a hyphen
function nameFromDir(dirPath) {
	return path.basename(dirPath).trim().toLowerCase().replace(/\s+/g, "-");
}

function findProjectName() {
	return nameFromDir(process.cwd());
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
	nameFromDir,
	findProjectName,
	getReleaseDir,
	getSSHKeyPath,
	getControlKeyPath,
	config
};
