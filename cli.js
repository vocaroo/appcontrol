#!/usr/bin/env node
const yargs = require("yargs/yargs");
const readlineSync = require("readline-sync");
const findApps = require("./findApps.js");
const createRelease = require("./createRelease.js");
const deploy = require("./deploy.js");
const getFingerprint = require("./getFingerprint.js");
const conf = require("./conf.js");
const {findProjectName} = require("./utils.js");

yargs(process.argv.slice(2))
	.command("info", "show info about deployment", {}, (argv) => {
		console.log("Welcome to AppControl");
		console.log("Current project name:", findProjectName());

		let apps = findApps();

		console.log("Detected apps: ", apps.map(appInfo => appInfo.name));
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
		if (!conf.get("email").value()) {
			let email = null;
			
			while (!email) {
				email = readlineSync.question("Enter an email address for letsencrypt notifications: ");
			}
			
			conf.set("email", email).write();
		}
		
		console.log(`Deploying to ${argv.target}`);
		deploy(argv.target);
	})
	.command("get-fingerprint <hostIP>", "Get the ed25519 fingerprint of the specified host", {}, (argv) => {
		getFingerprint(argv.hostIP);
	})
	.help()
	.argv;
