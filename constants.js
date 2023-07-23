const path = require("path");
const os = require("os");

exports.TOOL_NAME = "AppControl";
exports.TOOL_NAME_LOWERCASE = exports.TOOL_NAME.toLowerCase();
exports.LOCAL_DATA_DIR = ".appcontrol";
exports.LOCAL_CONFIG_FILE = "appcontrol.json";
exports.APP_CONFIG_FILE = "app.json";
exports.APP_META_FILE = "appMeta.json";
exports.CONTROL_KEY_DIR = exports.LOCAL_DATA_DIR + "/keys";
exports.KNOWN_HOSTS_PATH = path.join(os.homedir(), ".ssh/known_hosts");

// What properties of a server object can be used as a key
exports.VALID_SERVER_KEYS = ["ipv4", "ipv6", "hostname", "uniqueId"];

// Remote server script exit codes
exports.REMOTE_EXIT_CODE_WEBPATH_CONFLICT = 1
exports.REMOTE_EXIT_CODE_CERT_FAILED = 2
exports.REMOTE_EXIT_CODE_HOST_COMMAND_FAILED = 3
exports.REMOTE_EXIT_CODE_HOST_VERIFICATION_FAILED = 4
