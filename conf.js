const path = require("path");
const os = require("os");
const lowdb = require("lowdb");
const FileSync = require("lowdb/adapters/FileSync");
const constants = require("./constants.js");

const conf = lowdb(new FileSync(
	path.join(os.homedir(), `.${constants.TOOL_NAME_LOWERCASE}.json`)
));

conf.defaults({
}).write();

module.exports = conf;
