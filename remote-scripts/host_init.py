import os, sys, shutil
import constants
from pathlib import Path
from utils import runCommand
from host_utils import fromTemplate

print("Will init this server!")

deploymentName = sys.argv[1]
letsencryptThumbprint = sys.argv[2]
assert(len(deploymentName) > 0)
assert(len(letsencryptThumbprint) > 0)

print("Deployment name:", deploymentName)
print("Letsencrypt thumbprint:", letsencryptThumbprint)

os.makedirs(constants.HOSTSERVER_APPS_DIR, exist_ok = True)
os.makedirs(constants.HOSTSERVER_APPS_DIR + "/" + deploymentName, exist_ok = True)
os.makedirs(constants.HOSTSERVER_INSTALLED_APPS_DIR, exist_ok = True)
os.makedirs(constants.HOSTSERVER_CERTS_DIR, exist_ok = True)

# Install nginx
if shutil.which("nginx") == None:
	runCommand(["apt", "update"])
	runCommand(["apt", "install", "-y", "nginx"])
	assert shutil.which("nginx") != None

# Check for existence of appcontrol's customised nginx conf (via a magic string). If it doesn't exist yet, create a
# basic bootstrap one to handle the HTTP letsencrypt challenge

nginxConf = Path(constants.NGINX_CONF_PATH).read_text()

if constants.NGINX_CONF_MAGIC not in nginxConf:
	nginxConf = fromTemplate("nginx-conf-ssl-bootstrap.template", {
		"###LETSENCRYPT_ACCOUNT_THUMBPRINT###" : letsencryptThumbprint
	})
	
	# Write basic stub/bootstrap nginx conf
	Path(constants.NGINX_CONF_PATH).write_text(nginxConf)
	
	# Reload nginx
	runCommand(["systemctl", "--no-block", "reload", "nginx"])
