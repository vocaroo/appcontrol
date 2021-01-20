const fs = require("fs-extra");
const path = require("path");
const tmp = require("tmp");
const tar = require("tar");
const constants = require("./constants.js");
const findApps = require("./findApps.js");
const {findProjectName, makeFullAppName} = require("./utils.js");
const db = require("./db.js");

function getReleaseFile(releaseNumber) {
	return constants.RELEASE_DIR + `/release-${releaseNumber}.tar.gz`;
}

function getNextReleaseFile() {
	return getReleaseFile( db.get("latestReleaseNum").value() + 1);
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

	// create /tmp dir
	// copy builds to that dir
	// combine as a tar gz file
	// copy to release dir
	// ...naming in numbered order...
	// (remove old releases)

	let tmpDir = tmp.dirSync({
		prefix : constants.TOOL_NAME,
		unsafeCleanup : true
	}).name;

	console.log("temp dir:", tmpDir);

	// Copy all apps to temp dir
	for (let app of allApps) {
		fs.copySync(app.buildDir, tmpDir + "/" + makeFullAppName(app.name));
	}

	console.log("Compressing release...");

	// build as a tar gz file to release dir

	let files = fs.readdirSync(tmpDir);
	let releaseFile = getNextReleaseFile();

	tar.c({
		sync : true,
		gzip : true,
		strict : true,
		cwd : tmpDir,
		file : releaseFile
	}, files);

	console.log("New release saved to:", releaseFile);

	// Successful release, so increase release number
	db.update("latestReleaseNum", n => n + 1)
		.write();
};
