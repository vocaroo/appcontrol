
TOOL_NAME = "AppControl"
TOOL_NAME_LOWERCASE = TOOL_NAME.lower()

# on master server
CONTROLSERVER_SCRIPTS_DIR = "appcontrol-master-scripts"
CONTROLSERVER_DEPLOYMENTS_DIR = "appcontrol-master-deployments"
CONTROLSERVER_DEPLOYMENTS_INCOMING_DIR = "appcontrol-master-deployments-incoming"
CONTROLSERVER_CERTS_DIR = "appcontrol-master-certs"
CONTROLSERVER_CONF_PATH = "appcontrol-master.conf.json"

# on non master, "host", servers
HOSTSERVER_SCRIPTS_DIR = "appcontrol-host-scripts"
HOSTSERVER_APPS_DIR = "appcontrol-host-apps"
HOSTSERVER_CERTS_DIR = "appcontrol-host-certs"
HOSTSERVER_CONF_PATH = "appcontrol-host.conf.json"
HOSTSERVER_INSTALLED_APPS_DIR = "/var/lib/" + TOOL_NAME_LOWERCASE + "/installed_apps"
HOSTSERVER_APP_DATA_DIR = "/var/lib/" + TOOL_NAME_LOWERCASE + "/appdata"
HOSTSERVER_APP_LOG_DIR = "/var/log/" + TOOL_NAME_LOWERCASE
HOSTSERVER_APP_TEMP_DIR = "/tmp/" + TOOL_NAME_LOWERCASE

# Exit codes
REMOTE_EXIT_CODE_WEBPATH_CONFLICT = 1
REMOTE_EXIT_CODE_CERT_FAILED = 2
REMOTE_EXIT_CODE_HOST_COMMAND_FAILED = 3
REMOTE_EXIT_CODE_HOST_VERIFICATION_FAILED = 4

# Misc
CONTROL_KEY_NAME = "control-key"
KNOWN_HOSTS_PATH = ".ssh/known_hosts"
SERVERAPP_PORT_START = 9000
NGINX_CONF_PATH = "/etc/nginx/nginx.conf"
NGINX_CONF_MAGIC = "---APPCONTROL_MAGIC_IDENT---"
LOCAL_CONFIG_FILE = "appcontrol.json" # Ideally this should be copied acrosss from constants.js! (is repeated from there)
ACME_SH_PATH = "/root/.acme.sh/acme.sh"
SSHD_CONFIG_PATH = "/etc/ssh/sshd_config.d/appcontrol.conf"
HOST_VERIFICATION_MATCH_STR = "Host key verification failed"
