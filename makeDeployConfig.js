
// Given the config and a deploy target, make the server side deploy config
// This will be deployed to the master server as part of the named deployment.
// Should only contain things relevant to the deployment.
module.exports = function(config, target) {
	let deployConfig = {};
	
	// Copy letsencrypt block
	if (config.letsencrypt) {
		deployConfig.letsencrypt = config.letsencrypt;
	}
	
	// Copy only the relevant deploy target block
	deployConfig.deployment = config.deployments[target];
		
	return deployConfig;
}
