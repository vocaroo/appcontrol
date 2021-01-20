const fs = require("fs");

exports.isWebApp = false;

exports.detect = function(dirPath) {
	// detect "server.js" exists
	return fs.existsSync(dirPath + "/server.js");
};

exports.build = function(dirPath) {
	return dirPath; // No building necessary for generic server apps. Just copy it as is.
};
