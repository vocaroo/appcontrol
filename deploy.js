const util = require("util");
const process = require("process");
const child_process = require("child_process");
const path = require("path");
const assert = require("assert");
const fs = require("fs-extra");
const tmp = require("tmp");
const SSH = require("simple-ssh");
const constants = require("./constants.js");
const {globalDB, localDB} = require("./db.js");
const resetServer = require("./resetServer.js");
const makeDeployConfig = require("./makeDeployConfig.js");
const {getNumberedReleaseDir, getControlKeyPath, hostFromServer, getServerDefinition} = require("./utils.js");
const config = require("./config.js");

const REMOTE_SCRIPT_DIR = "appcontrol-master-scripts"; // directory only present on the control or master server
const REMOTE_DEPLOYMENTS_INCOMING_DIR = "appcontrol-master-deployments-incoming";
const MAIN_SSH_PRIVATE_KEY = fs.readFileSync(config.sshKey);
const HOST_VERIFICATION_MATCH_STR = "Host key verification failed"; // Finding this in ssh output means verification failed
const exec = util.promisify(child_process.exec);

class HostVerificationError extends Error {
	constructor(message) {
		super(message);
		this.name = "HostVerificationError";
	}
}

// sourceDir can be an array of sources
function rsync(host, sourceDir, destDir, extraArgs = []) {
	return new Promise((resolve, reject) => {
		let remoteShell = "ssh -oBatchMode=yes -i " + config.sshKey;
		let dest = "root@[" + host + "]:" + destDir;

		let rsyncProcess = child_process.spawn(
			"rsync",
			[
				"-rzl",
				"-e", remoteShell,
				"--delete",
				"--checksum",
				"--timeout=10"
			].concat(extraArgs, sourceDir, dest)
		);
		
		const stdoutOnData = (data) => {
			console.log(data.toString());
		}
		
		const stderrOnData = (data) => {
			console.log(data.toString());
			
			if (data.toString().includes(HOST_VERIFICATION_MATCH_STR)) {
				rsyncProcess.stdout.off("data", stdoutOnData);
				rsyncProcess.stderr.off("data", stderrOnData);
				rsyncProcess.off("error", processOnError);
				rsyncProcess.off("close", processOnClose);
				reject(new HostVerificationError(`Host ${host} key verification failed!`));
			}
		}
		
		const processOnError = (error) => {
			reject(error);
		}
		
		const processOnClose = (code) => {
			if (code == 0) {
				resolve();
			} else {
				console.error(`Rsync to ${host} failed with code ${code}, will retry...`);

				setTimeout(() => {
					resolve(rsync(host, sourceDir, destDir, extraArgs));
				}, 1000);
			}
		}

		rsyncProcess.stdout.on("data", stdoutOnData);
		rsyncProcess.stderr.on("data", stderrOnData);
		rsyncProcess.on("error", processOnError);
		rsyncProcess.on("close", processOnClose);
	});
}

function syncRemoteScripts(host) {
	return rsync(host, __dirname + "/remote-scripts/", REMOTE_SCRIPT_DIR);
}

function syncDeployment(host, deploymentDir) {
	return rsync(host, deploymentDir, REMOTE_DEPLOYMENTS_INCOMING_DIR + "/");
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
			localDB.set(`controlKeyCopiedStatus.${target}`, {})
				.write();

			console.log(`Control key did not exist for ${target}, creating...`);
			let stdout = child_process.execSync("ssh-keygen -t ed25519 -N \"\" -f" + keyPath);
			console.log(stdout.toString());
		} else {
			throw error;
		}
	}
}

async function copyControlKeyToHost(target, serverId, host) {
	if (localDB.get(`controlKeyCopiedStatus.${target}.${serverId}`).value()) {
		return; // Already copied for this target
	}

	let keyPath = getControlKeyPath(target);
	
	// This is untested when config.sshKey is anything other than the default ID
	// -f is required due to some... issues.... with the key not getting copied
	// (possibly due to ssh seeing that the IdentityFile works for login, despite the key we want to copy being different. not sure about that though!)
	// The copied status check above should prevent it being added again anyway.
	// It does mean if the local appcontrol state is deleted it could be added more than once.
	try {
		const {stdout, stderr} = await exec(`ssh-copy-id -i "${keyPath}" -o 'IdentityFile "${config.sshKey}"' -f root@${host}`);
	} catch (error) {
		if (error.message.includes(HOST_VERIFICATION_MATCH_STR)) {
			console.log(error.message);
			throw new HostVerificationError(`Host ${host} key verification failed!`);
		}
		
		throw error;
	}

	console.log("Copied key to", host);
	localDB.set(`controlKeyCopiedStatus.${target}.${serverId}`, true)
		.write();
}

async function copyControlKeyToServers(target, servers) {
	await Promise.all(servers.map(
		server => copyControlKeyToHost(target, server.uniqueId, hostFromServer(server))
	));
}

function getDeploymentName(target) {
	return config.name + "---" + target; // e.g. "MyProject---production"
}

function bundleDeployment(deployConfig, target, releaseDir, appNames) {
	let tmpDir = tmp.dirSync({
		prefix : constants.TOOL_NAME + "-deploy"
	}).name;

	let deploymentDir = tmpDir + "/" + getDeploymentName(target);

	console.log("Building deployment...", tmpDir, constants.LOCAL_CONFIG_FILE);

	fs.mkdirSync(deploymentDir);
	fs.mkdirSync(deploymentDir + "/apps");

	// copy *validated* appcontrol
	fs.writeJsonSync(deploymentDir + "/" + constants.LOCAL_CONFIG_FILE, deployConfig, {spaces : "\t"});

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

function chooseMasterServer(deployment) {
	if (deployment.masterServer) {
		return getServerDefinition(deployment.masterServer);
	}
	
	if (config.masterServer) {
		return getServerDefinition(config.masterServer);
	}
	
	// Fall back to first server in the deployment
	return deployment.servers[0];
}

module.exports = async function(target, releaseNumber = localDB.get("latestReleaseNum").value()) {
	let releaseDir = getNumberedReleaseDir(config.releaseDir, releaseNumber);
	console.log(`Deploying release number ${releaseNumber} to ${target}...`);
	
	let email = globalDB.get("email").value();
	assert(email, "No email defined in conf");

	const deployment = config.deployments[target];
	const servers = deployment.servers;

	if ( !(servers?.length > 0) ) {
		console.log(`No servers for "${target}" found in config, nothing to do.`);
		return;
	}
	
	// Check that fingerprint didn't change
	for (let server of servers) {
		let lastFingerprint = localDB.get(`lastFingerprints.${target}.${server.uniqueId}`).value();
		
		if (lastFingerprint && server.fingerprint != lastFingerprint) {
			// It changed.
			console.log(`Fingerprint for server ${hostFromServer(server)} changed. Will re-init...`);
			resetServer(server.uniqueId);
		}
		
		localDB.set(`lastFingerprints.${target}.${server.uniqueId}`, server.fingerprint)
			.write();
	}

	let controlServer = chooseMasterServer(deployment);
	let controlServerHost = hostFromServer(controlServer);
	
	console.log("Using master server", controlServer.hostname, controlServer.ipv4, controlServer.ipv6);
	
	// Ensure there is a ssh key for the control server
	ensureControlKey(target);

	console.log("Checking server control keys...");

	// Deploy it to every server in the target!
	await copyControlKeyToServers(target, servers);

	console.log("Checking control server...");

	// Sync remote scripts to control server
	await syncRemoteScripts(controlServerHost);
	
	// Init control server
	if (!globalDB.get(`controlServerInitStatus.${controlServer.uniqueId}`).value()) {		
		console.log("Control server initialising...");
		await runRemoteScript(controlServerHost, "control_init.py " + email);
		
		globalDB.set(`controlServerInitStatus.${controlServer.uniqueId}`, true)
			.write();
	}

	// Get all apps that are used by this deploy target
	let appsUsed = getAppsUsed(servers);

	// Create deploy package for the control server (apps, config, keys)
	const deployConfig = makeDeployConfig(config, target);
	let {deploymentDir, purgeDeploymentDir} = bundleDeployment(deployConfig, target, releaseDir, appsUsed);

	console.log("Deploying package to control server", controlServerHost);

	try {
		await syncDeployment(controlServerHost, deploymentDir);
	} finally {
		// Remove after has been deployed! May contain private keys.
		purgeDeploymentDir();
	}

	console.log("Control server deploying to others...");

	// Init control server
	await runRemoteScript(controlServerHost, "control_deploy.py " + email + " " + getDeploymentName(target));
	
	console.log("Done.");
}
