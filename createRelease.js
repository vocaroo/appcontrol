const fs = require("fs-extra");
const path = require("path");
const tmp = require("tmp");
const tar = require("tar");
const constants = require("./constants.js");
const findApps = require("./findApps.js");
const {findProjectName, makeFullAppName} = require("./utils.js");
const db = require("./db.js");

function getReleaseDir(releaseNumber) {
	return constants.RELEASE_DIR + `/release-${releaseNumber}`;
}

function getNextReleaseDir() {
	return getReleaseDir( db.get("latestReleaseNum").value() + 1);
}

module.exports = async function() {
	fs.ensureDirSync(constants.LOCAL_DATA_DIR);
	fs.ensureDirSync(constants.RELEASE_DIR);

	let apps = findApps();
	let allApps = apps.webApps.concat(apps.serverApps);

	// Build all apps, both web and server
	for (let app of allApps) {
		console.log("Building app...", app.name);

		let buildDir = app.detector.build(app.dir);
		console.log("Built to", buildDir);
		// Save build dir for later
		app.buildDir = buildDir;
	}

	let tmpDir = tmp.dirSync({
		prefix : constants.TOOL_NAME,
		unsafeCleanup : true
	}).name;

	console.log("Compressing apps to temp dir...", tmpDir);

	// Copy all apps to temp dir (compressing as tar.gz)
	for (let app of allApps) {
		tar.c({
			sync : true,
			gzip : true,
			strict : true,
			cwd : app.buildDir,
			file : tmpDir + "/" + makeFullAppName(app.name) + ".tar.gz"
		}, fs.readdirSync(app.buildDir));
	}

	let releaseDir = getNextReleaseDir();

	fs.copySync(tmpDir + "/", releaseDir);

	console.log("New release saved to:", releaseDir);

	// Successful release, so increase release number
	db.update("latestReleaseNum", n => n + 1)
		.write();
};
