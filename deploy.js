const util = require("util");
const process = require("process");
const child_process = require("child_process");
const path = require("path");
const assert = require("assert");
const fs = require("fs-extra");
const tmp = require("tmp");
const SSH = require("simple-ssh");
const constants = require("./constants.js");
const db = require("./db.js");
const conf = require("./conf.js");
const {validateConfig, validateAppName} = require("./validateConfig.js");
const {getReleaseDir, getSSHKeyPath, getControlKeyPath, findProjectName} = require("./utils.js");

const REMOTE_SCRIPT_DIR = "appcontrol-master-scripts"; // directory only present on the control or master server
const REMOTE_DEPLOYMENTS_DIR = "appcontrol-master-deployments";
const MAIN_SSH_PRIVATE_KEY = fs.readFileSync(getSSHKeyPath());
const exec = util.promisify(child_process.exec);

// sourceDir can be an array of sources
function rsync(host, sourceDir, destDir, extraArgs = []) {
	return new Promise((resolve, reject) => {
		let remoteShell = "ssh -oBatchMode=yes -i " + getSSHKeyPath();
		let dest = "root@" + host + ":" + destDir;

		let rsyncProcess = child_process.spawn(
			"rsync",
			[
				"-rzl",
				"-e", remoteShell,
				"--delete",
				"--timeout=10"
			].concat(extraArgs, sourceDir, dest)
		);

		rsyncProcess.stdout.on("data", (data) => {
			console.log(data.toString());
		});
		rsyncProcess.stderr.on("data", (data) => {
			console.log(data.toString());
		});
		rsyncProcess.on("error", (error) => {
			reject(error);
		});
		rsyncProcess.on("close", (code) => {
			if (code == 0) {
				resolve();
			} else {
				console.error(`Rsync to ${host} failed with code ${code}, will retry...`);

				setTimeout(() => {
					resolve(rsync(host, sourceDir, destDir, extraArgs));
				}, 1000);
			}
		});
	});
}

function syncRemoteScripts(host) {
	return rsync(host, __dirname + "/remote-scripts/", REMOTE_SCRIPT_DIR);
}

function syncDeployment(host, deploymentDir) {
	return rsync(host, deploymentDir, REMOTE_DEPLOYMENTS_DIR + "/");
}

// split some text into lines and print them one by one to console.log, ignoring empty (whitespace only) lines
function printStdLines(stdtext, linePrependText = "") {
	stdtext.split("\n").forEach(line => line.match(/\S/) && console.log(linePrependText + line));
}

// run a script, usually only on the control server
function runRemoteScript(host, scriptName) {
	return new Promise((resolve, reject) => {
		let ssh = new SSH({
			user : "root",
			host : host,
			key : MAIN_SSH_PRIVATE_KEY
		});

		ssh.exec("python3 -B " + REMOTE_SCRIPT_DIR + "/" + path.basename(scriptName), {
			exit : (code, stdout, stderr) => {
				printStdLines(stdout, "remote says: ");
				printStdLines(stderr, "remote says: ");

				if (code == 0) {
					console.log(`Remote script ${scriptName} on ${host} was successful`);
					resolve();
				} else {
					reject(Error(`Remote script ${scriptName} on server ${host} failed, exit code ${code}`));
				}
			}
		}).start({
			success : () => {
				console.log(`Connected to control server ${host}`);
			},
			fail : (error) => {
				console.error(error);
				console.error(`ssh connection to server ${host} failed, will retry...`);

				setTimeout(() => {
					resolve(runRemoteScript(host, scriptName));
				}, 1000);
			}
		});
	});
}

function ensureControlKey(target) {
	fs.ensureDirSync(constants.CONTROL_KEY_DIR);
	let keyPath = getControlKeyPath(target);

	try {
		fs.accessSync(keyPath);
	} catch (error) {
		if (error.code == "ENOENT") {
			// clear copied status flags in case the key for this target has been deleted and this is a new key
			// new key will then be copied on next deploy
			db.set(`controKeyCopiedStatus.${target}`, {})
				.write();

			console.log(`Control key did not exist for ${target}, creating...`);
			let stdout = child_process.execSync("ssh-keygen -t ed25519 -N \"\" -f" + keyPath);
			console.log(stdout.toString());
		} else {
			throw error;
		}
	}
}

function hostToProp(host) { // turn an IP address into a string that can be used as a lowdb object property
	return host.replace(/\./g, "-").replace(/:/g, "_");
}

async function copyControlKeyToHost(target, host) {
	if (db.get(`controKeyCopiedStatus.${target}.${hostToProp(host)}`).value()) {
		return; // Already copied for this target
	}

	let keyPath = getControlKeyPath(target);

	// This is untested when getSSHKeyPath is anything other than the default ID
	// -f is required due to some... issues.... with the key not getting copied
	// (possibly due to ssh seeing that the IdentityFile works for login, despite the key we want to copy being different. not sure about that though!)
	// The copied status check above should prevent it being added again anyway.
	// It does mean if the local appcontrol state is deleted it could be added more than once.
	const {stdout, stderr} = await exec(`ssh-copy-id -i "${keyPath}" -o 'IdentityFile "${getSSHKeyPath()}"' -f root@${host}`);
	//printStdLines(stdout.toString());
	//printStdLines(stderr.toString());

	console.log("Copied key to", host);
	db.set(`controKeyCopiedStatus.${target}.${hostToProp(host)}`, true)
		.write();
}

async function copyControlKeyToServers(target, servers) {
	await Promise.all(servers.map(
		server => copyControlKeyToHost(target, server.ip)
	));
}

function getDeploymentName(target) {
	return findProjectName() + "---" + target; // e.g. "MyProject---production"
}

function buildDeployment(validatedConfig, target, releaseDir, appNames) {
	let tmpDir = tmp.dirSync({
		prefix : constants.TOOL_NAME + "-deploy"
	}).name;

	let deploymentDir = tmpDir + "/" + getDeploymentName(target);

	console.log("Building deployment...", tmpDir, constants.LOCAL_CONFIG_FILE);

	fs.mkdirSync(deploymentDir);
	fs.mkdirSync(deploymentDir + "/apps");

	// copy *validated* appcontrol
	fs.writeJsonSync(deploymentDir + "/" + constants.LOCAL_CONFIG_FILE, validatedConfig, {spaces : "\t"});

	// Copy control key
	fs.copyFileSync(getControlKeyPath(target), deploymentDir + "/control-key");

	// Copy all relevant apps
	for (let appName of appNames) {
		try {
			fs.copySync(releaseDir + "/" + appName, deploymentDir + "/apps/" + appName)
		} catch (error) {
			if (error.code == "ENOENT") {
				console.log(`Error, app "${appName}" not found in release.\nPerhaps you need to create a release?`);
				process.exit(1);
			} else {
				throw error;
			}
		}
	}

	return {
		deploymentDir,
		purgeDeploymentDir : () => fs.removeSync(tmpDir)
	};
}

// Get a list of all apps used across the given servers
function getAppsUsed(servers) {
	let appsUsed = new Set();

	servers.forEach(server =>
		server.apps.forEach(appInfo => appsUsed.add(appInfo.app))
	);

	return Array.from(appsUsed);
}

module.exports = async function(target, releaseNumber = db.get("latestReleaseNum").value()) {
	// Validation
	target = validateAppName(target);
	let validatedConfig = validateConfig(fs.readJsonSync(constants.LOCAL_CONFIG_FILE), target); // This also may set some defaults

	let releaseDir = getReleaseDir(releaseNumber);
	console.log(`Deploying release number ${releaseNumber} to ${target}...`);

	let servers = validatedConfig[target];

	if ( !(servers?.length > 0) ) {
		console.log(`No servers for "${target}" found in config, nothing to do.`);
		return;
	}

	let controlServer = servers[0];

	// Ensure there is a ssh key for the control server
	ensureControlKey(target);

	console.log("Checking server control keys...");

	// Deploy it to every server in the target!
	await copyControlKeyToServers(target, servers);

	console.log("Checking control server...");

	// Sync remote scripts to control server
	await syncRemoteScripts(controlServer.ip);
	
	// Init control server
	try {
		let email = conf.get("email").value();
		assert(email, "No email defined in conf");
		
		console.log("Control server initialising...");
		await runRemoteScript(controlServer.ip, "control_init.py " + email);
	} catch (error) {
		console.log(error.message);
		console.log("Control server init failed.");
	}

	// Get all apps that are used by this deploy target
	let appsUsed = getAppsUsed(servers);

	// Build deploy package for the control server (apps, config, keys)
	let {deploymentDir, purgeDeploymentDir} = buildDeployment(validatedConfig, target, releaseDir, appsUsed);

	console.log("Deploying package to control server", controlServer.ip);

	try {
		await syncDeployment(controlServer.ip, deploymentDir);
	} finally {
		// Remove after has been deployed! May contain private keys.
		purgeDeploymentDir();
	}

	console.log("Control server deploying to others...");

	// Init control server
	try {
		await runRemoteScript(controlServer.ip, "control_deploy.py " + getDeploymentName(target));
	} catch (error) {
		console.log(error.message); // Don't want to display the full stack, since the error was server side
		console.log("Control server deploy failed.");
	}

	console.log("Done.");
}
