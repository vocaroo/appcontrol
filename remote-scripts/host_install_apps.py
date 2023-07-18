# Install all apps that have been deployed to this server
import os, json, secrets, shutil, importlib, glob, sys, pwd
import constants
from pathlib import Path
from utils import runCommand, ConfigStore
from host_utils import (
	fromTemplate, loadRuntimes, getAppInstalledPath, getInstanceCount, getServiceName, formatEnvForSystemd,
	genUserName, genDataGroupUserName, getAppLogDir, getAppDataDir, getAppTempDir
)
from build_nginx_config import buildNginxConf

print("Will install apps on this server!")

letsencryptThumbprint = sys.argv[1]
assert(len(letsencryptThumbprint) > 0)

# Import runtime plugins
runtimes = loadRuntimes()

# A place to store some local state for host server
localConf = ConfigStore(constants.HOSTSERVER_CONF_PATH)

# All apps and redirects found across all deployments
allApps = []
allRedirects = []

# All used runtimes
usedRuntimes = set()

for deploymentName in os.listdir(constants.HOSTSERVER_APPS_DIR):
	# Find all redirects in this deployment
	with open(constants.HOSTSERVER_APPS_DIR + "/" + deploymentName + "/server.json", "r") as fp:
		serverBlock = json.load(fp)
		
		if "redirects" in serverBlock:
			for redirect in serverBlock["redirects"]:
				allRedirects.append(redirect)
	
	# Find all apps
	for dirent in os.scandir(constants.HOSTSERVER_APPS_DIR + "/" + deploymentName):
		if dirent.is_dir(): # might be a server.json which is not a dir
			appName = dirent.name
			
			with open(constants.HOSTSERVER_APPS_DIR + "/" + deploymentName + "/" + appName + "/appMeta.json", "r") as fp:
				appMeta = json.load(fp)
			
			if "runtime" in appMeta:
				usedRuntimes.add(appMeta["runtime"])

			if "dataGroup" in appMeta:
				username = genDataGroupUserName(deploymentName, appMeta["dataGroup"])
			else:
				username = genUserName(deploymentName, appName)
			
			allApps.append({
				"appName" : appName,
				"deploymentName" : deploymentName,
				"domain" : appMeta.get("domain", None),
				"webPath" : appMeta.get("webPath", "/"),
				"instancesPerCPU" : appMeta.get("instancesPerCPU", 0),
				"isWebApp" : appMeta["isWebApp"],
				"runtime" : appMeta.get("runtime", None),
				"main" : appMeta.get("main", None),
				"env" : appMeta.get("env", {}),
				"username" : username,
				"dataDir" : getAppDataDir(deploymentName, username),
				"logDir" : getAppLogDir(deploymentName, appName, username)
			})

# Validate: Check that no two apps share the same domain and webPath
domainAndWebPathSet = set()

for appInfo in allApps:
	if appInfo["domain"]:
		hash = str(appInfo["domain"]) + appInfo["webPath"]
		assert hash not in domainAndWebPathSet, ("Same domain and webPath in more than one app: " + appInfo["appName"])
		domainAndWebPathSet.add(hash)

# We increment the start port by 1000 each time, just in case some old processes were
# hanging on to ports for a while when shutting down.

portIndex = localConf.get("lastPortStart", constants.SERVERAPP_PORT_START - 1000)
portIndex += 1000

if portIndex >= constants.SERVERAPP_PORT_START + 5000:
	portIndex = constants.SERVERAPP_PORT_START

localConf.set("lastPortStart", portIndex)

# Go through all apps again and determine port ranges and real instance counts
# Also create users etc

for appInfo in allApps:
	if not appInfo["isWebApp"]:
		# Ports
		instanceCount = getInstanceCount(appInfo["instancesPerCPU"])
		appInfo["instanceCount"] = instanceCount
		appInfo["portRangeStart"] = portIndex
		portIndex += instanceCount
		
		# Create users for server apps only
		# add user if doesn't exist already
		try:
			pwd.getpwnam(appInfo["username"])
		except KeyError:
			runCommand(["useradd", appInfo["username"]])
		
		# Create log directory
		os.makedirs(appInfo["logDir"], exist_ok = True)
		shutil.chown(appInfo["logDir"], appInfo["username"], appInfo["username"])
		
		# Create logrotate config for this app
		Path("/etc/logrotate.d/" + constants.TOOL_NAME_LOWERCASE + "." + appInfo["deploymentName"] + "." + appInfo["appName"]).write_text(fromTemplate("logrotate.template", {
			"###LOG_DIR###" : appInfo["logDir"],
			"###USER###" : appInfo["username"]
		}))

		# Create data dir, with correct permissions
		os.makedirs(appInfo["dataDir"], mode=0o755, exist_ok = True)
		shutil.chown(appInfo["dataDir"], appInfo["username"], appInfo["username"])


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

# Group apps AND redirects by domain name
# If an app doesn't have a domain, omit it. Won't be routed to by nginx, e.g. a server daemon.
thingsByDomain = {}

for appInfo in allApps:
	domain = appInfo["domain"]

	if domain:
		if domain not in thingsByDomain:
			thingsByDomain[domain] = {"apps" : [], "redirects" : []}
		
		thingsByDomain[domain]["apps"].append(appInfo)

for redirectInfo in allRedirects:
	domain = redirectInfo["domain"]

	if domain:
		if domain not in thingsByDomain:
			thingsByDomain[domain] = {"apps" : [], "redirects" : []}
			
		thingsByDomain[domain]["redirects"].append(redirectInfo)

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
				"###USER###" : appInfo["username"],
				"###PORT###" : str(appInfo["portRangeStart"] + i),
				"###APP_DATA_DIR###" : appInfo["dataDir"],
				"###APP_LOG_DIR###" : appInfo["logDir"],
				"###APP_TEMP_DIR###" : getAppTempDir(appInfo["deploymentName"], appInfo["username"]),
				"###ENVIRONMENT###" : formatEnvForSystemd({
					# Use env vars from the runtime and also the app.json
					# app.json having precedence
					**runtime.getEnv(runtimeVersion),
					**appInfo["env"]
				}),
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
nginxConf = buildNginxConf(newInstallDir, thingsByDomain, letsencryptThumbprint)

# (Don't write it unless the conf building actually succeeded above)
with open(constants.NGINX_CONF_PATH, "w") as fp:
	fp.write(nginxConf)

# Then, reload nginx!
runCommand(["systemctl", "--no-block", "reload", "nginx"])

# Finally, purge the old install dir(s)!
for dir in oldInstallDirs:
	shutil.rmtree(constants.HOSTSERVER_INSTALLED_APPS_DIR + "/" + dir)
