const fs = require("fs-extra");
const path = require("path");
const assert = require("assert");
const {nameFromDir} = require("./utils.js");

const appDetectors = [
	require("./appdetect/createReactApp.js"),
	require("./appdetect/genericServerApp.js")
];

function getDirNames(dirPath) { // get list of subdirs, ignoring hidden dirs
	let dirents = fs.readdirSync(dirPath, {withFileTypes : true});
	return dirents.filter(dirent => dirent.isDirectory() && !dirent.name.startsWith(".")).map(dirent => dirent.name);
}

// find all apps, client and server, to be deployed
module.exports = function findApps(startPath = "./") {
	let apps = {
		webApps : [],
		serverApps : []
	};

	let dirNames = getDirNames(startPath);

	for (let dir of dirNames) {
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

		if (detectedAs) {
			let appInfo = {
				name : nameFromDir(dir),
				dir : dir,
				detector : detectedAs
			};

			if (detectedAs.isWebApp) {
				apps.webApps.push(appInfo);
			} else {
				apps.serverApps.push(appInfo);
			}
		} else {
			// Recurse
			let subDirApps = findApps(dir);
			apps.webApps = apps.webApps.concat(subDirApps.webApps);
			apps.serverApps = apps.serverApps.concat(subDirApps.serverApps);
		}
	}

	return apps;
};
