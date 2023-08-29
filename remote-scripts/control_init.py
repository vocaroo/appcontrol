import sys, os, re
import constants
from utils import runCommand, ConfigStore

print("Initialising control server...")

import both_init

email = sys.argv[1]
assert(len(email) > 0)

os.makedirs(constants.CONTROLSERVER_CERTS_DIR, exist_ok = True)
os.makedirs(constants.CONTROLSERVER_DEPLOYMENTS_INCOMING_DIR, exist_ok = True)
os.makedirs(constants.CONTROLSERVER_DEPLOYMENTS_DIR, exist_ok = True)

# A place to store some local state for control server
localConf = ConfigStore(constants.CONTROLSERVER_CONF_PATH)

# Initial setup and install of some things on this master server
runCommand(["apt", "update"])
runCommand(["apt", "install", "-y", "python3-pip"])
runCommand([sys.executable, "-m", "pip", "install", "asyncssh"])

# Write cron job to propagate certs
def writeCertPropagationCron():
	cronFilePath = "/etc/cron.daily/" + constants.TOOL_NAME_LOWERCASE + "-propagate-certs"
	
	with open(cronFilePath, "w") as fp:
		certPropagateScriptPath = constants.CONTROLSERVER_SCRIPTS_DIR + "/control_propagate_certs.py"
		fp.write("#!/bin/sh\ncd /root && python3 " + certPropagateScriptPath + " >> /var/log/" + constants.TOOL_NAME_LOWERCASE + "-propagate-certs.log")
	
	os.chmod(cronFilePath, 0o755)

writeCertPropagationCron()

# Install and set up acme.sh if not already
if not os.path.isdir(".acme.sh"):
	print("Installing acme.sh")
	print( runCommand(["wget", "-O", "/tmp/acme.sh", "https://raw.githubusercontent.com/acmesh-official/acme.sh/master/acme.sh"]) )
	print( runCommand(["sh", "/tmp/acme.sh", "--install-online", "-m", email]) )
	assert os.path.isdir(".acme.sh")
	print( runCommand([constants.ACME_SH_PATH, "--set-default-ca", "--server", "letsencrypt"]) )
	registerAccountStdout = runCommand([constants.ACME_SH_PATH, "--register-account"])
	print( registerAccountStdout )
	thumbprint = re.search(r"ACCOUNT_THUMBPRINT='([-_a-zA-Z0-9]+)'", registerAccountStdout).group(1)
	print(f"Letsencrypt account thumbprint [{thumbprint}]")
	# Save letsencrypt account thumbprint
	localConf.set("letsencryptThumbprint", thumbprint)
	localConf.set("email", email)

assert localConf.get("letsencryptThumbprint"), "No letsencrypt thumbprint found"

# Everything succeeded...
localConf.set("initialised", True)
