const path = require("path");
const os = require("os");

exports.TOOL_NAME = "AppControl";
exports.TOOL_NAME_LOWERCASE = exports.TOOL_NAME.toLowerCase();
exports.LOCAL_DATA_DIR = ".appcontrol";
exports.LOCAL_CONFIG_FILE = "appcontrol.json";
exports.APP_META_FILE = "appMeta.json";
exports.CONTROL_KEY_DIR = exports.LOCAL_DATA_DIR + "/keys";
exports.KNOWN_HOSTS_PATH = path.join(os.homedir(), ".ssh/known_hosts");
