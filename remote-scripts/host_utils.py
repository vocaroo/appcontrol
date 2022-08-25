import os, importlib
from pathlib import Path
import constants

def getCertPrivkeyPath(domain):
	return constants.HOSTSERVER_CERTS_DIR + "/" + domain + ".key.pem"

def getCertFullchainPath(domain):
	return constants.HOSTSERVER_CERTS_DIR + "/" + domain + ".fullchain.pem"

def fromTemplate(templateName, substitutions):
	template = Path(constants.HOSTSERVER_SCRIPTS_DIR + "/templates/" + templateName).read_text()
	for original, replacement in substitutions.items():
	    template = template.replace(original, replacement)
	return template

def loadRuntimes():
	runtimes = {}
	
	for fileName in os.listdir(constants.HOSTSERVER_SCRIPTS_DIR + "/runtimes"):
		runtimeName, ext = os.path.splitext(fileName)
		
		if ext == ".py":
			runtimes[runtimeName] = importlib.import_module("runtimes." + runtimeName).Runtime()
	
	return runtimes

def getAppInstalledPath(newInstallDir, appInfo):
	return newInstallDir + "/" + appInfo["deploymentName"] + "/" + appInfo["appName"]

def getInstanceCount(instancesPerCPU):
	return instancesPerCPU * os.cpu_count() if instancesPerCPU > 0 else 1

def getServiceName(deploymentName, appName, instanceNum):
	return constants.TOOL_NAME_LOWERCASE + "---" + deploymentName + "---" + appName + "---" + str(instanceNum) + ".service"

# Takes a dict and outputs a string containing "Environment=..." statements for a systemd unit file
def formatEnvForSystemd(env):
	str = ""
	for key, val in env.items():
		str += f"Environment={key}={val}\n"
	return str
