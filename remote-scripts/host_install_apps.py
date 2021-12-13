# Install all apps that have been deployed to this server
import os, json, secrets, shutil
import constants
from utils import runCommand
from host_utils import getCertPrivkeyPath, getCertFullchainPath, fromTemplate

print("Will install apps on this server!")

# All apps found across all deployments
allApps = []

for deploymentName in os.listdir(constants.HOSTSERVER_APPS_DIR):
	for appName in os.listdir(constants.HOSTSERVER_APPS_DIR + "/" + deploymentName):
		with open(constants.HOSTSERVER_APPS_DIR + "/" + deploymentName + "/" + appName + "/appMeta.json", "r") as fp:
			appMeta = json.load(fp)

		allApps.append({
			"appName" : appName,
			"deploymentName" : deploymentName,
			"domain" : appMeta.get("domain", None),
			"webPath" : appMeta.get("webPath", "/"),
			"instancesPerCPU" : appMeta.get("instancesPerCPU", 0),
			"isWebApp" : appMeta["isWebApp"]
		})

# Validate: Check that no two apps share the same domain and webPath
domainAndWebPathSet = set()

for appInfo in allApps:
	hash = str(appInfo["domain"]) + appInfo["webPath"]
	assert hash not in domainAndWebPathSet, ("Same domain and webPath in more than one app: " + appInfo["appName"])
	domainAndWebPathSet.add(hash)

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

def getAppInstalledPath(appInfo):
	return newInstallDir + "/" + appInfo["deploymentName"] + "/" + appInfo["appName"]

# copy all apps (web and server) to subdirs in it. just the release dir.
# ( /deploymentName/appName )
for appInfo in allApps:
	shutil.copytree(
		constants.HOSTSERVER_APPS_DIR + "/" + appInfo["deploymentName"] + "/" + appInfo["appName"] + "/release",
		getAppInstalledPath(appInfo)
	)

def buildNginxConf(appsByDomain):
	confServerBlocks = []
	confUpstreamBlocks = []
	portIndex = constants.SERVERAPP_PORT_START

	# Add a server block for each domain name
	# Each may in turn contain several apps
	for domain, appInfos in appsByDomain.items():
		rootApp = None
		defaultRoot = "/var/www/html"
		confLocationBlocks = []

		for appInfo in appInfos: # For each app of this domain
			# There is a top level, root, web app
			if appInfo["webPath"] == "/":
				assert appInfo["isWebApp"] == True, "Root app must be a web app"
				rootApp = appInfo
			else:
				if appInfo["isWebApp"]:
					# For other than the default, root, web app, add a location block
					confLocationBlocks.append(fromTemplate("nginx-webapp-location.template", {
						"###WEBPATH###" : appInfo["webPath"].strip("/"), # conf already has slashes
						"###ROOT_DIR###" : getAppInstalledPath(appInfo)
					}))
				else: # Server app
					# Create an upstream block

					upstreamName = appInfo["deploymentName"] + "-" + appInfo["appName"]
					# Default to just one instance in total if "instancesPerCPU" is set to zero (the default)
					# Otherwise... an instance per CPU!
					instanceCount = appInfo["instancesPerCPU"] * os.cpu_count() if appInfo["instancesPerCPU"] > 0 else 1

					confUpstreamBlocks.append(fromTemplate("nginx-serverapp-upstream.template", {
						"###UPSTREAM_NAME###" : upstreamName,
						"###SERVERS###" : "\n".join(["server 127.0.0.1:" + str(portIndex + i) + " max_fails=0;" for i in range(0, instanceCount)])
					}))

					# Move the next available port forward by the number of instances
					portIndex += instanceCount

					# Create a location block
					confLocationBlocks.append(fromTemplate("nginx-serverapp-location.template", {
						"###WEBPATH###" : appInfo["webPath"].strip("/"), # conf already has slashes
						"###UPSTREAM_NAME###" : upstreamName
					}))

		if rootApp:
			defaultRoot = getAppInstalledPath(rootApp)

		confServerBlocks.append(fromTemplate("nginx-server-block.template", {
			"###SSL_CERT_FULLCHAIN###" : "/root/" + getCertFullchainPath(domain),
			"###SSL_CERT_KEY###" : "/root/" + getCertPrivkeyPath(domain),
			"###DEFAULT_ROOT###" : defaultRoot,
			"###DOMAIN_NAME###" : domain,
			"###APP_LOCATION_BLOCKS###" : "\n".join(confLocationBlocks)
		}))

	return fromTemplate("nginx-conf.template", {
		"###APP_UPSTREAM_BLOCKS###" : "\n".join(confUpstreamBlocks),
		"###SERVER_BLOCKS###" : "\n".join(confServerBlocks)
	})

# THEN, create nginx config!
nginxConf = buildNginxConf(appsByDomain)

# (Don't write it unless the conf building actually succeeded above)
with open(constants.NGINX_CONF_PATH, "w") as fp:
	fp.write(nginxConf)

# Then, reload nginx!
runCommand(["systemctl", "--no-block", "reload", "nginx"])

# Finally, purge the old install dir(s)!
for dir in oldInstallDirs:
	shutil.rmtree(constants.HOSTSERVER_INSTALLED_APPS_DIR + "/" + dir)
