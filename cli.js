#!/usr/bin/env node
const fs = require("fs-extra");
const constants = require("./constants.js");

// Create local data dir before we access any DB below.
fs.ensureDirSync(constants.LOCAL_DATA_DIR);

const yargs = require("yargs/yargs");
const readlineSync = require("readline-sync");
const config = require("./config.js");
const {globalDB} = require("./db.js");
const {HostVerificationError, RemoteScriptFailedError} = require("./errors.js");

function cmdRelease() {
	console.log("will release");
	require("./createRelease.js")();
}

function cmdDeploy(target) {	
	if (!globalDB.get("email").value()) {
		let email = null;
		
		while (!email) {
			email = readlineSync.question("Enter an email address for letsencrypt notifications: ");
		}
		
		globalDB.set("email", email).write();
	}
	
	console.log(`Deploying to ${target}`);
	require("./deploy.js")(target).then(() => {
		console.log("Done.");
	}).catch(error => {
		console.log(error);
		console.log("!!!!!!!!!! DEPLOYMENT FAILED !!!!!!!!!!");
		
		if (error instanceof HostVerificationError) {
			console.log("Host key verification of the master server failed. If you reinstalled or reprovisioned "
				+ "the master server, try running the reset server command.");
		}
		
		if (error instanceof RemoteScriptFailedError) {
			if (error.exitCode == constants.REMOTE_EXIT_CODE_CERT_FAILED) {
				console.log("Certificate request failed!");
				console.log("Maybe something is wrong with your letsencrypt config, or you didn't set up "
						+ "DNS records from a domain to a server yet.");
			} else if (error.exitCode == constants.REMOTE_EXIT_CODE_HOST_VERIFICATION_FAILED) {
				console.log("Host key verification of a server failed. If you reinstalled or reprovisioned a server, "
					+ "try running the reset server command.");
			}
		}
	});
}

yargs(process.argv.slice(2))
	.command("info", "Show info about deployment", {}, (argv) => {
		console.log("Welcome to AppControl");
		console.log("Current project name:", config.name);

		let apps = require("./findApps.js")();

		console.log("Detected apps: ", apps.map(appInfo => appInfo.name));
	})
	.command("init", "Create a basic deployment config in the current directory", {}, (argv) => {
		require("./init.js")();
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
	.command("addserver", "Add a server definition to the global database", {}, argv => {
		require("./addServer.js")();
	})
	.command("get-fingerprint <hostIP>", "Get the ed25519 fingerprint of the specified host", {}, (argv) => {
		require("./getFingerprint.js")(argv.hostIP);
	})
	.command("reset <server>", "This must be called if a host or control server has been reinstalled or otherwise had its data removed.", {}, (argv) => {
		require("./resetServer.js")(argv.server);
	})
	.command("hello", "...", {}, (argv) => {
		console.log(fs.readFileSync(__dirname + "/.vocaroo-ascii-art", {encoding : "utf8"}));
		console.log("               Hello from Vocaroo!\n");
	})
	.demandCommand(1, "Hey there, how are you?")
	.help()
	.argv;
