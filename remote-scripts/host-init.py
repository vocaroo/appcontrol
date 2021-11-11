import os, sys, shutil
import constants
from utils import getProjectNameAndTarget, runCommand

print("Will init this server!")

deploymentName = sys.argv[1]
assert(len(deploymentName) > 0)

print("Deployment name:", deploymentName)

os.makedirs(constants.HOSTSERVER_DEPLOYMENTS_DIR, exist_ok = True)
os.makedirs(constants.HOSTSERVER_DEPLOYMENTS_DIR + "/" + deploymentName, exist_ok = True)

# Install nginx
if shutil.which("nginx") == None:
    runCommand(["apt", "install", "-y", "nginx"])
    assert shutil.which("nginx") != None
