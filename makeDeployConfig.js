
// Given the config and a deploy target, make the server side deploy config
// This will be deployed to the master server as part of the named deployment.
// Should only contain things relevant to the deployment.
module.exports = function(config, target) {
	let deployConfig = {};
	
	deployConfig.letsencrypt = config.letsencrypt;
	deployConfig.env = config.env;
	deployConfig.envClient = config.envClient;
	deployConfig.envServer = config.envServer;
	deployConfig.envShared = config.envShared;
	deployConfig.envApp = config.envApp;
	
	// Copy only the relevant deploy target block
	deployConfig.deployment = config.deployments[target];
		
	return deployConfig;
}
