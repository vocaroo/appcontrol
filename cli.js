#!/usr/bin/env node
const yargs = require("yargs/yargs");
const findApps = require("./findApps.js");
const createRelease = require("./createRelease.js");
const deploy = require("./deploy.js");
const getFingerprint = require("./getFingerprint.js");
const {findProjectName} = require("./utils.js");

yargs(process.argv.slice(2))
	.command("info", "show info about deployment", {}, (argv) => {
		console.log("Welcome to AppControl");
		console.log("Current project name:", findProjectName());

		let apps = findApps();

		console.log("Detected web apps: ", apps.webApps.map(appInfo => appInfo.name));
		console.log("Detected server apps: ", apps.serverApps.map(appInfo => appInfo.name));
	})
	.command("release", "create a numbered release", {}, (argv) => {
		console.log("will release");
		// store in ".appcontrol" in current dir
		createRelease();
	})
	.command("deploy <target>", "deploy latest release to either staging or production", yargs => {
		yargs.positional("target", {
			describe : "deploy target",
			choices : ["staging", "production"]
		})
	}, argv => {
		console.log(`Deploying to ${argv.target}`);
		deploy(argv.target);
	})
	.command("get-fingerprint <hostIP>", "Get the ed25519 fingerprint of the specified host", {}, (argv) => {
		console.log(`Getting fingerprint of ${argv.hostIP}...`);
		getFingerprint(argv.hostIP);
	})
	.help()
	.argv;
