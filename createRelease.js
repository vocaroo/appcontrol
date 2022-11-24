const fs = require("fs-extra");
const path = require("path");
const child_process = require("child_process");
const process = require("process");
const tmp = require("tmp");
const constants = require("./constants.js");
const findApps = require("./findApps.js");
const {getReleaseDir, readJson} = require("./utils.js");
const db = require("./db.js");

function getNextReleaseDir() {
	return getReleaseDir( db.get("latestReleaseNum").value() + 1);
}

module.exports = async function() {
	fs.ensureDirSync(constants.RELEASE_DIR);

	let allApps = findApps();
	
	// Read the app.json and/or get defaults from appDetector
	for (let app of allApps) {
		let detectorDefaults = app.detector ? app.detector.defaults : {};
				
		app.appMeta = {
			...detectorDefaults,
			...readJson(`${app.dir}/app.json`) // Override with app.json, if one exists
		};
		
		// If it doesn't have a "main", then it's a web app.
		app.appMeta.isWebApp = !app.appMeta.hasOwnProperty("main");
	}

	// Build all apps, both web and server
	for (let app of allApps) {
		console.log("Building app...", app.name);
		
		// If a buildCmd is specified in app.json, we use that
		// Otherwise if there is an app detector, and it provides a build method, we use that to build
		// Otherwise, we don't build at all and assume doesn't need building
		
		if ("buildCmd" in app.appMeta) {
			try {
				child_process.execSync(app.appMeta.buildCmd, {cwd : app.dir});
			} catch (error) {
				console.log(`Error building using custom build command ${app.appMeta.buildCmd}`);
				throw error;
			}
			
			// use buildPath from app.json if present, otherwise use "build" as a default
			app.buildDir = path.join(app.dir, app.appMeta.buildPath || "build");
		} else if (app.detector?.build) {
			app.buildDir = app.detector.build(app.dir);
		} else {
			// No build, just use as is
			// Still will take from a buildPath if one was specified, otherwise use the app's top level dir
			if ("buildPath" in app.appMeta) {
				app.buildDir = path.join(app.dir, app.appMeta.buildPath);
			} else {
				app.buildDir = app.dir;
			}
			
			// If the build dir is the app's top level dir, we need to know
			// And maybe delete some things that we don't want copied (app.json)
			if (app.buildDir == app.dir) {
				app.usedOriginalDir = true;
			}
		}
		
		console.log("Built to ", app.buildDir);
	}

	let tmpDir = tmp.dirSync({
		prefix : constants.TOOL_NAME + "-release",
		unsafeCleanup : true
	}).name;

	console.log("Compressing apps to temp dir...", tmpDir);

	// Copy all apps to temp dir
	for (let app of allApps) {
		let appTmpReleaseDir = `${tmpDir}/${app.name}/release`;
		fs.copySync(app.buildDir, appTmpReleaseDir);
		
		// If we just copied the entire source dir, then remove any app.json that was copied across
		if (app.usedOriginalDir) {
			try {
				fs.unlinkSync(appTmpReleaseDir + "/app.json");
			} catch (error) {
				if (error.code != "ENOENT") {
					throw error;
				}
			}
		}

		// Create a meta file for each app that records app type plus contents of app.json
		fs.writeJsonSync(
			tmpDir + `/${app.name}/appMeta.json`,
			app.appMeta,
			{spaces : "\t"}
		);
	}

	/*for (let app of allApps) {
		tar.c({
			sync : true,
			gzip : true,
			strict : true,
			cwd : app.buildDir,
			file : tmpDir + "/" + app.name + ".tar.gz"
		}, fs.readdirSync(app.buildDir));
	}*/

	let releaseDir = getNextReleaseDir();

	fs.copySync(tmpDir + "/", releaseDir);

	console.log("New release saved to:", releaseDir);

	// Successful release, so increase release number
	db.update("latestReleaseNum", n => n + 1)
		.write();
};
