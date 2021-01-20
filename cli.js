#!/usr/bin/env node
const yargs = require("yargs/yargs");
const findApps = require("./findApps.js");
const createRelease = require("./createRelease.js");
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
		console.log(`will deploy to ${argv.target}`);
	})
	.help()
	.argv;
