# Install all apps that have been deployed to this server
import os, json, secrets, shutil, importlib, glob
import constants
from pathlib import Path
from utils import runCommand
from host_utils import fromTemplate, loadRuntimes, getAppInstalledPath, getInstanceCount, getServiceName, formatEnvForSystemd
from build_nginx_config import buildNginxConf

print("Will install apps on this server!")

# Import runtime plugins
runtimes = loadRuntimes()

# All apps found across all deployments
allApps = []

# All used runtimes
usedRuntimes = set()

for deploymentName in os.listdir(constants.HOSTSERVER_APPS_DIR):
	for appName in os.listdir(constants.HOSTSERVER_APPS_DIR + "/" + deploymentName):
		with open(constants.HOSTSERVER_APPS_DIR + "/" + deploymentName + "/" + appName + "/appMeta.json", "r") as fp:
			appMeta = json.load(fp)
		
		if "runtime" in appMeta:
			usedRuntimes.add(appMeta["runtime"])

		allApps.append({
			"appName" : appName,
			"deploymentName" : deploymentName,
			"domain" : appMeta.get("domain", None),
			"webPath" : appMeta.get("webPath", "/"),
			"instancesPerCPU" : appMeta.get("instancesPerCPU", 0),
			"isWebApp" : appMeta["isWebApp"],
			"runtime" : appMeta.get("runtime", None),
			"main" : appMeta.get("main", None)
		})

# Go through all apps again and determine port ranges and real instance counts

portIndex = constants.SERVERAPP_PORT_START

for appInfo in allApps:
	if not appInfo["isWebApp"]:
		instanceCount = getInstanceCount(appInfo["instancesPerCPU"])
		appInfo["instanceCount"] = instanceCount
		appInfo["portRangeStart"] = portIndex
		portIndex += instanceCount

# Validate: Check that no two apps share the same domain and webPath
domainAndWebPathSet = set()

for appInfo in allApps:
	hash = str(appInfo["domain"]) + appInfo["webPath"]
	assert hash not in domainAndWebPathSet, ("Same domain and webPath in more than one app: " + appInfo["appName"])
	domainAndWebPathSet.add(hash)

# return (name, version) from a string like "node:16". version may be None.
def splitRuntimeVersion(runtimeName):
	name = runtimeName
	version = None
	
	if ":" in runtimeName:	# runtime has a version number
		name, version = runtimeName.split(":")
	
	return name, version


# Install runtimes (e.g. nodejs)
# Ensure all runtimes (and correct versions) are installed on this host
for runtimeName in usedRuntimes:
	name, version = splitRuntimeVersion(runtimeName)	
	# Install runtime, passing the version
	runtimes[name].install(version)

# Group apps by domain name
appsByDomain = {}

for appInfo in allApps:
	domain = appInfo["domain"]

	if domain in appsByDomain:
		appsByDomain[domain].append(appInfo)
	else:
		appsByDomain[domain] = [appInfo]

# First, find old install dir(s)
# Should only be a single dir, but we'll treat it as many just in case there were ever some errors
# that led to multiple dirs.
oldInstallDirs = os.listdir(constants.HOSTSERVER_INSTALLED_APPS_DIR)

# create a NEW installed www/app dir, with some random ID in it
# e.g. /var/lib/appcontrol/asufhajghahg
newInstallDir = constants.HOSTSERVER_INSTALLED_APPS_DIR + "/" + secrets.token_hex(16)
os.makedirs(newInstallDir, exist_ok = True)

# copy all apps (web and server) to subdirs in it. just the release dir.
# ( /deploymentName/appName )
for appInfo in allApps:
	shutil.copytree(
		constants.HOSTSERVER_APPS_DIR + "/" + appInfo["deploymentName"] + "/" + appInfo["appName"] + "/release",
		getAppInstalledPath(newInstallDir, appInfo)
	)

# Find existing systemd service units
previousServices = set([os.path.basename(f) for f in glob.glob("/etc/systemd/system/" + constants.TOOL_NAME_LOWERCASE + "*")])
currentServices = set()

# Create systemd service units for all server apps
for appInfo in allApps:
	if not appInfo["isWebApp"]:
		# Create one or more service instances
		for i in range(appInfo["instanceCount"]):
			serviceName = getServiceName(appInfo["deploymentName"], appInfo["appName"], i)
			runtimeName, runtimeVersion = splitRuntimeVersion(appInfo["runtime"])
			runtime = runtimes[runtimeName]
			
			workingDirectory = getAppInstalledPath(newInstallDir, appInfo)
			mainScriptPath = workingDirectory + "/" + appInfo["main"]
			
			systemdConfig = fromTemplate("systemd-service.template", {
				"###PORT###" : str(appInfo["portRangeStart"] + i),
				"###ENVIRONMENT###" : formatEnvForSystemd(runtime.getEnv(runtimeVersion)),
				"###WORKING_DIRECTORY###" : workingDirectory,
				"###EXEC_CMD###" : runtime.getRunCommand(mainScriptPath, runtimeVersion)
			})
			
			Path("/etc/systemd/system/" + serviceName).write_text(systemdConfig)
			currentServices.add(serviceName)

# Remove no longer present services

servicesToRemove = previousServices - currentServices

for serviceName in servicesToRemove:
	runCommand(["systemctl", "disable", serviceName])
	runCommand(["systemctl", "--no-block", "stop", serviceName]) # no-blocking for graceful stop
	os.remove("/etc/systemd/system/" + serviceName)

# Enable and (re)start desired services
# (we need restart for existing units, and it appears to work for starting new units too...)
for serviceName in currentServices:
	runCommand(["systemctl", "enable", serviceName])
	runCommand(["systemctl", "--no-block", "restart", serviceName])


# THEN, create nginx config!
nginxConf = buildNginxConf(newInstallDir, appsByDomain)

# (Don't write it unless the conf building actually succeeded above)
with open(constants.NGINX_CONF_PATH, "w") as fp:
	fp.write(nginxConf)

# Then, reload nginx!
runCommand(["systemctl", "--no-block", "reload", "nginx"])

# Finally, purge the old install dir(s)!
for dir in oldInstallDirs:
	shutil.rmtree(constants.HOSTSERVER_INSTALLED_APPS_DIR + "/" + dir)