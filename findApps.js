const fs = require("fs-extra");
const path = require("path");
const assert = require("assert");
const constants = require("./constants.js");
const {appNameFromDir} = require("./utils.js");

const EXCLUDED_DIRS = new Set(["node_modules"]);

// Require all contents of the ./appdetect dir
const appDetectors = fs.readdirSync(path.join(__dirname, "appdetect")).map(fileName => require("./appdetect/" + fileName));

function getDirNames(dirPath) { // get list of subdirs, ignoring hidden dirs
	let dirents = fs.readdirSync(dirPath, {withFileTypes : true});
	return dirents.filter(dirent => dirent.isDirectory() && !dirent.name.startsWith(".")).map(dirent => dirent.name);
}

// find all apps, client and server, to be deployed
module.exports = function findApps(startPath = "./") {
	let apps = [];
	
	// To ensure no duplicates
	let appNameSet = new Set();

	let dirNames = getDirNames(startPath);

	for (let dir of dirNames) {
		if (EXCLUDED_DIRS.has(dir)) {
			continue;
		}
		
		dir = path.join(startPath, dir); // may be recursing into subdir

		let detectedAs = null;
		let detectedCount = 0; // keep count as must only detect as a single type!

		for (let appDetector of appDetectors) {
			if (appDetector.detect(dir)) {
				detectedAs = appDetector;
				detectedCount ++;
			}
		}

		assert(detectedCount <= 1, "App detected as multiple types");

		// Either detected by an appdetector OR
		// not auto detected, but a custom app using an app.json file
		if (detectedAs || fs.existsSync(`${dir}/${constants.APP_CONFIG_FILE}`)) {
			let appInfo = {
				name : appNameFromDir(dir),
				dir : dir,
				detector : detectedAs
			};
			
			apps.push(appInfo);
			
			//need to ensure that a name doesn't appear twice, since spaces will be converted to hyphens, this is possible
			// e.g. "my app" and "my-app" will clash.
			assert(!appNameSet.has(appInfo.name), `Two apps with the same name detected (${appInfo.name})`);
			appNameSet.add(appInfo.name);
		} else {
			// Recurse
			apps = apps.concat(findApps(dir));
		}
	}
	
	return apps;
};
