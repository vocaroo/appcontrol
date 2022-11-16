#!/usr/bin/env node
const yargs = require("yargs/yargs");
const readlineSync = require("readline-sync");
const findApps = require("./findApps.js");
const createRelease = require("./createRelease.js");
const deploy = require("./deploy.js");
const getFingerprint = require("./getFingerprint.js");
const resetServer = require("./resetServer.js");
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
	.command("deploy <target>", "deploy latest release to a named target, e.g. staging or production", yargs => {
		yargs.positional("target", {
			describe : "deploy target"
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
	.command("reset <hostIP>", "This must be called if a host or control server has been reinstalled or otherwise had its data removed", {}, (argv) => {
		resetServer(argv.hostIP);
		// alert that new fingerprint should also be set
		console.log("This host has been reset. Run deploy now.");
		console.log("If the server OS was reinstalled remember to update the fingerprint in the config file wherever necessary or deployment will fail.")
	})
	.demandCommand(1, "Hey there, how are you?")
	.help()
	.argv;
