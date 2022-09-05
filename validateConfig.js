const assert = require("assert");
const {validateAppName} = require("./utils.js");

// Validate the deploy config, returning a minimal config with some things removed
// Used before the config is sent to the control server
// Validates only the specific target, removes stuff for other targets
module.exports = function validateConfig(config, target) {
	let validated = {};
	
	// Special character used to separate things in names on control server
	assert(!target.includes("---"), "Deploy target name must not contain three hyphens together");

	assert(config.email, "No email in config, required for letsencrypt");

	// Validation of all servers in a target
	// Check for duplicate app names within a server
	// Set some defaults
	for (let server of config[target]) {
		// Check for duplicate app names within server block
		let appNameSet = new Set();

		for (let appInfo of server.apps) {
			// validate (and possibly transform) name first
			appInfo.app = validateAppName(appInfo.app);
			
			assert(!appNameSet.has(appInfo.app), "Duplicate apps in server block!");
			assert(!appInfo.app.includes("---"), "App name must not contain three hyphens.");
			appNameSet.add(appInfo.app);
			
			// Validate webPath, don't want weird stuff getting into nginx regex
			assert(!appInfo.webPath || /^[-_a-zA-Z0-9/]+$/.test(appInfo.webPath), `webPath contained an invalid character: ${appInfo.webPath}`);
		}
	}

	validated.email = config.email;
	validated.letsencrypt = config.letsencrypt;
	validated[target] = config[target]; // Copy only the given target

	return validated;
}
