const fs = require("fs-extra");
const readlineSync = require("readline-sync");
const constants = require("./constants");
const {getGlobalServerDefinitions, hostFromServer} = require("./utils.js");

function serverToStrLong(server) {
	return hostFromServer(server) + (server.hostname ? ` (${server.hostname})` : "");
}

function getServerKey(server) {
	if (server.hostname) {
		return server.hostname;
	} else {
		return hostFromServer(server);
	}
}

function getAllPossibleServerKeys(servers) {
	let keys = new Set();
	
	for (let server of servers) {
		for (let keyName of constants.VALID_SERVER_KEYS) {
			server[keyName] && keys.add(server[keyName]);
		}
	}
	
	return keys;
}

module.exports = function() {
	const deployConfigPath = constants.LOCAL_CONFIG_FILE;
	
	console.log("This will create a simple configuration for deploying a single app to a single server.");
	
	if (fs.existsSync(deployConfigPath)) {
		console.log(`*** Warning: The deploy config file ${deployConfigPath} already exists, will not continue! ***`);
		return;
	}
	
	const servers = getGlobalServerDefinitions();
	const serverNames = servers.map(server => serverToStrLong(server));
	const allPossibleServerKeys = getAllPossibleServerKeys(servers);
	
	if (servers.length == 0) {
		console.log("Error: Please add at least one remote server using <appcontrol addserver> first!");
		return;
	}
	
	let deployServerKey = getServerKey(servers[0]);
	let masterServerKey = getServerKey(servers[0]);
		
	if (servers.length > 1) {
		let serverIndex;
		
		console.log("\nAvailable servers:", serverNames);
		deployServerKey = readlineSync.question(
			"\nPlease enter a server to host your app (hostname or IP address):\n> ",
			{limit : input => input}
		);
		
		if (!allPossibleServerKeys.has(deployServerKey)) {
			console.log(`\n*** Notice: server ${deployServerKey} not found in server definitions. Please add `
					+ "it before you deploy! ***");
		}
		
		masterServerKey = readlineSync.question("\nPlease enter a master server (hostname or IP address, default:"
		 		+ " same as the app server):\n> ");
		
		if (masterServerKey) {
			if (!allPossibleServerKeys.has(masterServerKey)) {
				console.log(`\n*** Notice: server ${masterServerKey} not found in server definitions. `
						+ "Please add it before you deploy! ***");
			}
		} else {
			masterServerKey = deployServerKey;
		}
	}
	
	const subdirs = fs.readdirSync("./").filter(name => name != constants.LOCAL_DATA_DIR);
	
	console.log("\nAvailable sub directories:", subdirs);
	
	let appName = readlineSync.question(
		"\nEnter the name of the sub directory which will contain your app to be deployed:\n> ",
		{limit : input => input}
	);

	let mainFile = null;
	let nodeVersion = null;
	
	if (!readlineSync.keyInYNStrict("\nIs your app a client side web app? (Not a NodeJS server app)\n> ")) {
		mainFile = readlineSync.question(
			"\nYour app is a server side NodeJS app. What is the app entry point or main file? (default: server.js)\n> ",
			{defaultInput : "server.js"}
		);
		nodeVersion = readlineSync.questionInt(
			"\nWhat Node version are you targeting? (e.g. 20, default: always the latest version)\n> ",
			{defaultInput : 0}
		);
		
		if (nodeVersion == 0) {
			nodeVersion = null;
		}
	}
	
	let buildCmd = null;
	let buildDir = null;
	
	if (readlineSync.keyInYNStrict("\nDoes your app have a build command or script?\n> ")) {
		buildCmd = readlineSync.question(
			'\nPlease enter the build command (default: "npm build"):\n> ',
			{defaultInput : "npm build"}
		);
		
		buildDir = readlineSync.question(
			'\nPlease enter the build directory (default: "build"):\n> ',
			{defaultInput : "build"}
		);
	}
	
	let domain = null;
	let webPath = null;
	
	if (readlineSync.keyInYNStrict("\nDoes your app have a domain name?\n> ")) {
		domain = readlineSync.question(
			'\nPlease enter the domain name (e.g. "my.example.com"):\n> ',
			{defaultInput : null}
		);
		webPath = readlineSync.question(
			'\nWhat web path will your app be at? (e.g. "/" or "/my-app", default is "/"):\n> ',
			{defaultInput : "/"}
		);
	}
	
	// Create the config files
		
	let deployConfig = {
		"deployments" : {
			"production" : {
				"masterServer" : masterServerKey,
				"servers" : {
				}
			}
		}
	};
	
	deployConfig.deployments.production.servers[deployServerKey] = {
		"apps" : [
			{
				"app" : appName,
				"domain" : domain || undefined,
				"webPath" : (domain && webPath) ? webPath : undefined
			}
		]
	};
	
	let appConfig = {
		runtime : mainFile ? (nodeVersion ? `node:${nodeVersion}` : "node") : undefined,
		main : mainFile || undefined,
		buildCmd : buildCmd || undefined,
		buildDir : buildDir || undefined
	};
		
	// create appcontrol.json with a basic deploy config
	fs.writeJsonSync(deployConfigPath, deployConfig, {spaces : "\t"});
	
	// create an app.json within the app dir
	const appConfigPath = `${appName}/${constants.APP_CONFIG_FILE}`;
	fs.ensureDirSync(appName); // ensure dir
	fs.writeJsonSync(appConfigPath, appConfig, {spaces : "\t"});
	
	console.log("\nAnswer summary:", {
		deployServerKey,
		masterServerKey,
		appName,
		mainFile,
		buildCmd,
		buildDir,
		domain,
		webPath
	});
	
	console.log("\nCreated deploy config", deployConfigPath);
	console.log("Created app config", appConfigPath);
	console.log("\nALL DONE!");
}
