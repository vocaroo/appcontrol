const lowdb = require("lowdb");
const FileSync = require("lowdb/adapters/FileSync");
const constants = require("./constants.js");

const db = lowdb(new FileSync(constants.LOCAL_DATA_DIR + "/database.json"));

db.defaults({
	latestReleaseNum : 0
}).write();

module.exports = db;
