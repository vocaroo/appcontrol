const assert = require("assert");
const path = require("path");
const crypto = require("crypto");
const fs = require("fs-extra");
const constants = require("./constants.js");
const {readJson, appNameFromDir, validateAppName, getServerDefinition} = require("./utils.js");
const {globalDB, localDB} = require("./db.js");
const {ServerNotDefinedError} = require("./errors.js");

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
	// Key specified in config?
	if (config.sshKey) {
		return config.sshKey;
	}
	
	// Otherwise, was there a key in global store?
	const globalKey = globalDB.get("sshKey").value();
	
	if (globalKey) {
		if (path.isAbsolute(globalKey)) {
			return globalKey;
		} else {
			return path.join(process.env.HOME, globalKey);
		}
	}
	
	// Otherwise, try this one
	return path.join(process.env.HOME, ".ssh/id_ed25519");
}

function getMasterServer() {
	if (config.masterServer) {
		return config.masterServer;
	}
	
	const globalMasterServer = globalDB.get("masterServer").value();
	
	if (globalMasterServer) {
		return globalMasterServer;
	}
	
	return null;
}

function validatedConfig() {
	let validated = {};
	
	validated.name = getProjectName();
	validated.releaseDir = getReleaseDir();
	validated.sshKey = getSSHKeyPath();
	validated.masterServer = getMasterServer() || undefined;
	validated.excludeApps = Array.isArray(config.excludeApps) ? config.excludeApps : [];
	
	if (config.deployments) {
		validated.deployments = {};
		
		for (let target in config.deployments) {
			validateAppName(target);
			
			const deployBlock = config.deployments[target];
			
			assert(deployBlock.servers, `No servers in target ${target}`);
			
			let serverTemplates = deployBlock.serverTemplates || {};

			// Validation of all servers in a target
			// Check for duplicate app names within a server
			// Set some defaults
			for (let [serverKey, server] of Object.entries(deployBlock.servers)) {
				
				// If the server is a string and not an object, then it is the name of a server template
				// And so we replace it with the contents of the template.
				if (typeof server == "string") {
					assert(serverTemplates[server], `Server template "${server}" not found.`);
					
					// must be a deep clone!!
					deployBlock.servers[serverKey] = structuredClone(serverTemplates[server]);
					server = deployBlock.servers[serverKey];
				}
				
				// Check for duplicate app names within server block
				let appNameSet = new Set();

				for (let appInfo of server.apps) {
					// validate (and possibly transform) name first
					appInfo.app = validateAppName(appInfo.app);
					
					assert(!appNameSet.has(appInfo.app), "Duplicate apps in server block!");
					appNameSet.add(appInfo.app);
					
					// Validate webPath, don't want weird stuff getting into nginx regex
					assert(!appInfo.webPath || /^[-_a-zA-Z0-9/]+$/.test(appInfo.webPath), `webPath contained an invalid character: ${appInfo.webPath}`);
					
					// Transform any singular "domain" property into a domains array
					if (appInfo.domain) {
						if (!appInfo.domains) {
							appInfo.domains = [];
						}
						
						appInfo.domains.push(appInfo.domain);
						delete appInfo.domain;
					}
				}
			}
			
			// Convert key-value server definitions (server hostname or IP -> server block) into a simple array.
			// Also reading the server IP, fingerprint etc from the globalDB.
			
			let serverArray = [];
			
			for (const [serverKey, server] of Object.entries(deployBlock.servers)) {
				// The serverKey might be the hostname, ipv4 or ipv6 address.
				try {				
					serverArray.push({
						...getServerDefinition(serverKey),
						...server
					});
				} catch (error) {
					if (error instanceof ServerNotDefinedError) {
						console.log(`*** Warning: server ${serverKey} in deploy config was not found in server definitions. `
								+ "This server will be ignored and will not be deployed to! ***\n");
					} else {
						throw error;
					}
				}
			}
			
			validated.deployments[target] = deployBlock;
			validated.deployments[target].servers = serverArray;
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
