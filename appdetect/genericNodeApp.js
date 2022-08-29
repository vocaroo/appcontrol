const fs = require("fs");
const path = require("path");
const {readJson} = require("../utils.js");

exports.defaults = {
	runtime : "node", // node latest
	main : "server.js"
};

// We detect by:
// either the app's main file (as specified in app.json) ends in .js
// or if there is no main specified, we check for the existence of server.js

exports.detect = function(dirPath) {
	let appJson = readJson(`${dirPath}/app.json`);
	
	if ("main" in appJson) {
		// Detect if main in app.json exists and is a JS file
		return path.extname(appJson.main).toLowerCase() == ".js" && fs.existsSync(`${dirPath}/${appJson.main}`);
	} else {
		// Otherwise, fall back to detecting if default main file (server.js) exists
		return fs.existsSync(`${dirPath}/${exports.defaults.main}`);
	}
};

// No building necessary for generic server apps. Just copy it as is.
exports.build = null;
