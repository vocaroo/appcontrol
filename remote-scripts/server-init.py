import os, sys
import constants
from utils import getProjectNameAndTarget

print("Will init this server!")

deploymentName = sys.argv[1]
assert(len(deploymentName) > 0)

print("Deployment name:", deploymentName)

def ensureDir(path):
    try:
        os.mkdir(path)
    except FileExistsError:
        pass

ensureDir(constants.DEPLOYMENTS_DIR)
ensureDir(constants.DEPLOYMENTS_DIR + "/" + deploymentName)
