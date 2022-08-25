const fs = require("fs-extra");
const path = require("path");
const child_process = require("child_process");

exports.isWebApp = true;

// No runtime for static web apps
exports.defaults = {};

exports.detect = function(dirPath) {
	// detect existence of "react-scripts build" in package.json
	try {
		const package = fs.readJSONSync(dirPath + "/package.json");

		if (package.scripts?.build == "react-scripts build") {
			return true;
		}
	} catch (error) {
		if (error.code != "ENOENT") {
			throw error;
		}
	}

	return false;
};

// build the app at the given path, returning the build dir
exports.build = function(dirPath) {
	try {
		child_process.execSync(`yarn --cwd "${dirPath}" build`);
	} catch (error) {
		console.log("Error building create-react-app project", dirPath);
		throw error;
	}

	return path.join(dirPath, "build/");
};
