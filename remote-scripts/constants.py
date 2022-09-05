
TOOL_NAME = "AppControl"
TOOL_NAME_LOWERCASE = TOOL_NAME.lower()

# on master server
CONTROLSERVER_SCRIPTS_DIR = "appcontrol-master-scripts"
CONTROLSERVER_DEPLOYMENTS_DIR = "appcontrol-master-deployments"
CONTROLSERVER_CERTS_DIR = "appcontrol-master-certs"
CONTROLSERVER_CONF_PATH = "appcontrol-master.conf.json"

# on non master, "host", servers
HOSTSERVER_SCRIPTS_DIR = "appcontrol-host-scripts"
HOSTSERVER_APPS_DIR = "appcontrol-host-apps"
HOSTSERVER_CERTS_DIR = "appcontrol-host-certs"
HOSTSERVER_CONF_PATH = "appcontrol-host.conf.json"
HOSTSERVER_INSTALLED_APPS_DIR = "/var/lib/" + TOOL_NAME_LOWERCASE + "/installed_apps"

# Misc
CONTROL_KEY_NAME = "control-key"
KNOWN_HOSTS_PATH = ".ssh/known_hosts"
SERVERAPP_PORT_START = 9000
NGINX_CONF_PATH = "/etc/nginx/nginx.conf"
NGINX_CONF_MAGIC = "---APPCONTROL_MAGIC_IDENT---"
LOCAL_CONFIG_FILE = "appcontrol.json" # Ideally this should be copied acrosss from constants.js! (is repeated from there)
