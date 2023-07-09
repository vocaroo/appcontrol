#!/usr/bin/env node
const fs = require("fs-extra");
const yargs = require("yargs/yargs");
const readlineSync = require("readline-sync");
const constants = require("./constants.js");
const config = require("./config.js");
const conf = require("./conf.js");

function initProject() {
	fs.ensureDirSync(constants.LOCAL_DATA_DIR);
}

function cmdRelease() {
	console.log("will release");
	initProject();
	require("./createRelease.js")();
}

function cmdDeploy(target) {
	initProject();
	
	if (!conf.get("email").value()) {
		let email = null;
		
		while (!email) {
			email = readlineSync.question("Enter an email address for letsencrypt notifications: ");
		}
		
		conf.set("email", email).write();
	}
	
	console.log(`Deploying to ${target}`);
	require("./deploy.js")(target).catch(error => {
		console.log(error);
		console.log("!!!!!!!!!! DEPLOYMENT FAILED !!!!!!!!!!");
	});
}

yargs(process.argv.slice(2))
	.command("info", "Show info about deployment", {}, (argv) => {
		console.log("Welcome to AppControl");
		console.log("Current project name:", config.name);

		let apps = require("./findApps.js")();

		console.log("Detected apps: ", apps.map(appInfo => appInfo.name));
	})
	.command("release", "Create a numbered release", {}, argv => {
		cmdRelease();
	})
	.command("deploy <target>", "Deploy latest release to a named target, e.g. staging or production", yargs => {
		yargs.positional("target", {
			describe : "deploy target"
		})
	}, argv => {
		cmdDeploy(argv.target);
	})
	.command("quickrelease <target>", "Release and deploy in one step", yargs => {
		yargs.positional("target", {
			describe : "deploy target"
		})
	}, argv => {
		cmdRelease();
		cmdDeploy(argv.target);
	})
	.command("get-fingerprint <hostIP>", "Get the ed25519 fingerprint of the specified host", {}, (argv) => {
		require("./getFingerprint.js")(argv.hostIP);
	})
	.command("reset <hostIP>", "This must be called if a host or control server has been reinstalled or otherwise had its data removed", {}, (argv) => {
		initProject();
		require("./resetServer.js")(argv.hostIP);
		// alert that new fingerprint should also be set
		console.log("This host has been reset. Run deploy now.");
		console.log("If the server OS was reinstalled remember to update the fingerprint in the config file wherever necessary or deployment will fail.")
	})
	.demandCommand(1, "Hey there, how are you?")
	.help()
	.argv;
