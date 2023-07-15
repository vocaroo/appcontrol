const assert = require("assert");
const path = require("path");
const crypto = require("crypto");
const fs = require("fs-extra");
const constants = require("./constants.js");
const {readJson, appNameFromDir, validateAppName} = require("./utils.js");
const {globalDB, localDB} = require("./db.js");

const config = readJson(constants.LOCAL_CONFIG_FILE);

// maybe should be in utils.js
function getProjectUniqueId() {
	let projectUniqueId = localDB.get("projectUniqueId").value();
	
	if (!projectUniqueId) {
		projectUniqueId = crypto.randomUUID();
		
		localDB.set("projectUniqueId", projectUniqueId)
			.write();
	}
	
	return projectUniqueId;
}

function getExternalReleaseSubdir() {
	// for when releases are stored in some other global dir externally to the local dir
	return getProjectName().substr(0, 12) + "-" + getProjectUniqueId();
}

function getProjectName() {
	if (config.name) {
		return validateAppName(config.name);
	} else {
		// Otherwise, name the project after its directory
		// use same format as an app name
		return appNameFromDir(process.cwd());
	}
}

function getReleaseDir() {
	const localReleaseDir = config.releaseDir;
	const globalReleaseDir = globalDB.get("releaseDir").value();

	if (localReleaseDir) {
		return path.join(localReleaseDir, getExternalReleaseSubdir());
	} else if (globalReleaseDir) {
		return path.join(globalReleaseDir, getExternalReleaseSubdir());
	} else {
		return path.join(constants.LOCAL_DATA_DIR, "releases");
	}
}

function getSSHKeyPath() {
	if (config.sshKey) {
		return config.sshKey;
	}
	
	return path.join(process.env.HOME, ".ssh/id_ed25519");
}

function validatedConfig() {
	let validated = {};
	
	validated.name = getProjectName(config);
	validated.releaseDir = getReleaseDir(config);
	validated.sshKey = getSSHKeyPath();
	
	if (config.deployments) {
		validated.deployments = {};
		
		for (let target in config.deployments) {
			validateAppName(target);
			
			const deployBlock = config.deployments[target];
			
			assert(deployBlock.servers, `No servers in target ${target}`);

			// Validation of all servers in a target
			// Check for duplicate app names within a server
			// Set some defaults
			for (let server of deployBlock.servers) {
				// Check for duplicate app names within server block
				let appNameSet = new Set();

				for (let appInfo of server.apps) {
					// validate (and possibly transform) name first
					appInfo.app = validateAppName(appInfo.app);
					
					assert(!appNameSet.has(appInfo.app), "Duplicate apps in server block!");
					appNameSet.add(appInfo.app);
					
					// Validate webPath, don't want weird stuff getting into nginx regex
					assert(!appInfo.webPath || /^[-_a-zA-Z0-9/]+$/.test(appInfo.webPath), `webPath contained an invalid character: ${appInfo.webPath}`);
				}
			}
			
			validated.deployments[target] = deployBlock;
		}
	}

	validated.letsencrypt = config.letsencrypt;
	validated.env = config.env;
	validated.envClient = config.envClient;
	validated.envServer = config.envServer;
	validated.envShared = config.envShared;
	validated.envApp = config.envApp;

	return validated;
}

module.exports = validatedConfig();
