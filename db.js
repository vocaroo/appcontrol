const path = require("path");
const os = require("os");
const lowdb = require("lowdb");
const FileSync = require("lowdb/adapters/FileSync");
const constants = require("./constants.js");

// Global store, in user's home
const globalDB = lowdb(new FileSync(
	path.join(os.homedir(), `.${constants.TOOL_NAME_LOWERCASE}.json`)
));

// local per-project store, in project dir
const localDB = lowdb(new FileSync(constants.LOCAL_DATA_DIR + "/database.json"));

globalDB.defaults({
}).write();

localDB.defaults({
	latestReleaseNum : 0
}).write();

module.exports = {
	globalDB,
	localDB
};
