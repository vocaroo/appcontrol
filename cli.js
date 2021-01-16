#!/usr/bin/env node
const yargs = require("yargs/yargs");
const fs = require("fs-extra");
const path = require("path");

function getDirNames(path) {
	let dirents = fs.readdirSync(path, {withFileTypes : true});
	return dirents.filter(dirent => dirent.isDirectory()).map(dirent => dirent.name);
}

function isCreactReactApp(dirPath) {
	// detect scripts.build == "react-scripts build" in package.json
	try {
		const package = fs.readJSONSync(dirPath + "/package.json");

		if (package?.scripts?.build == "react-scripts build") {
			return true;
		}
	} catch (error) {
		if (error.code != "ENOENT") {
			throw error;
		}
	}

	return false;
}

function isGenericServerApp(dirPath) {
	// detect "server.js" exists
	return fs.existsSync(dirPath + "/server.js");
}

// find all apps, client and server, to be deployed
function findApps(startPath = "./") {
	let apps = {
		webApps : [],
		serverApps : []
	};

	let dirNames = getDirNames(startPath);

	for (let dir of dirNames) {
		dir = path.join(startPath, dir); // may be recursing into subdir

		if (isCreactReactApp(dir)) {
			apps.webApps.push(dir);
		} else if (isGenericServerApp(dir)) {
			apps.serverApps.push(dir);
		} else {
			// Recurse
			let subDirApps = findApps(path.join(startPath, dir));
			apps.webApps = apps.webApps.concat(subDirApps.webApps);
			apps.serverApps = apps.serverApps.concat(subDirApps.serverApps);
		}
	}

	return apps;
}

yargs(process.argv.slice(2))
	.command("info", "show info about deployment", {}, (argv) => {
		console.log("Will show info...");
		let apps = findApps();

		console.log("Found web apps: ", apps.webApps);
		console.log("Found server apps: ", apps.serverApps);
	})
	.command("release", "create a numbered release", {}, (argv) => {
		console.log("will release");
		// store in ".appcontrol" in current dir
	})
	.command("deploy <target>", "deploy latest release to either staging or production", yargs => {
		yargs.positional("target", {
			describe : "deploy target",
			choices : ["staging", "production"]
		})
	}, argv => {
		console.log(`will deploy to ${argv.target}`);
	})
	.help()
	.argv
