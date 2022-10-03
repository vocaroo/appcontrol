import os, importlib, hashlib
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

def getAppLogDir(deploymentName, appName):
	return constants.HOSTSERVER_APP_LOG_DIR + "/" + deploymentName + "/" + appName

def getAppDataDir(username):
	return constants.HOSTSERVER_APP_DATA_DIR + "/" + username

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

def genUserName(deploymentName, appName):
	# Format is (truncated app name)_(truncated hash of ("appname:" + app name))_(truncated hash of project/deploymentname)
	# Max 32 chars
	return appName[:10] + "_" + hashlib.sha256(("appname:" + appName).encode()).hexdigest()[:8] + "_" + hashlib.sha256(deploymentName.encode()).hexdigest()[:8]

def genDataGroupUserName(deploymentName, dataGroup):
	# Format is (truncated group name)_(truncated hash of ("datagroup:" + group name))_(truncated hash of project/deploymentname)
	# Max 32 chars
	# "appname:" / "datagroup:" strings prevents any clashes with app names and data groups.
	return dataGroup[:10] + "_" + hashlib.sha256(("datagroup:" + dataGroup).encode()).hexdigest()[:8] + "_" + hashlib.sha256(deploymentName.encode()).hexdigest()[:8]
