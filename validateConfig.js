const assert = require("assert");

// lower case and replace any spaces with a hyphen
// used for both app names and also some other things (target name, project name...)
function validateAppName(name) {
	name = name.trim().toLowerCase().replace(/\s+/g, "-");
	assert(/^[a-z][-_a-z0-9]+$/.test(name), `Invalid app name or other name: ${name}`);
	assert(!name.includes("---"), `App name or other name must not contain three hyphens: ${name}`);
	return name;
}

// Validate the deploy config, returning a minimal config with some things removed
// Used before the config is sent to the control server
// Validates only the specific target, removes stuff for other targets
function validateConfig(config, target) {
	let validated = {};
	
	validateAppName(target);
	
	assert(target in config, `Target "${target}" not found`);

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
			appNameSet.add(appInfo.app);
			
			// Validate webPath, don't want weird stuff getting into nginx regex
			assert(!appInfo.webPath || /^[-_a-zA-Z0-9/]+$/.test(appInfo.webPath), `webPath contained an invalid character: ${appInfo.webPath}`);
		}
	}

	validated.letsencrypt = config.letsencrypt;
	validated[target] = config[target]; // Copy only the given target

	return validated;
}

module.exports = {
	validateConfig, validateAppName
};
