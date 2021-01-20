const path = require("path");

// lower case and replace any spaces with a hyphen
function nameFromDir(dirPath) {
	return path.basename(dirPath).trim().toLowerCase().replace(/\s+/g, "-");
}

function findProjectName() {
	return nameFromDir(process.cwd());
}

function makeFullAppName(appName) {
	return findProjectName() + "-" + appName;
}

module.exports = {
	nameFromDir,
	findProjectName,
	makeFullAppName
};
