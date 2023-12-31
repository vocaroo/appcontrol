from host_utils import fromTemplate, getAppInstalledPath, getCertPrivkeyPath, getCertFullchainPath

def addAppLocationBlock(appInfo, upstreamBlockNames, confUpstreamBlocks, confLocationBlocks, newInstallDir):
	if appInfo["isWebApp"]:
		# For other than the default, root, web app, add a location block
		confLocationBlocks.append(fromTemplate("nginx-webapp-location.template", {
			"###WEBPATH###" : appInfo["webPath"].strip("/"), # conf already has slashes
			"###ROOT_DIR###" : getAppInstalledPath(newInstallDir, appInfo)
		}))
	else: # Server app
		# Create an upstream block
		upstreamName = appInfo["deploymentName"] + "-" + appInfo["appName"]

		# ensure only one upstream block for this given deployment/app combination
		# this is required as an app location block can appear in multiple domain names on the same server
		# but we must only have one upstream for all of these
		if upstreamName not in upstreamBlockNames:
			upstreamBlockNames.add(upstreamName)
			
			# Default to just one instance in total if "instancesPerCPU" is set to zero (the default)
			# Otherwise... an instance per CPU!
			instanceCount = appInfo["instanceCount"]

			confUpstreamBlocks.append(fromTemplate("nginx-serverapp-upstream.template", {
				"###UPSTREAM_NAME###" : upstreamName,
				"###SERVERS###" : "\n"
					.join(["server localhost:" + str(appInfo["portRangeStart"] + i) + " max_fails=0;" for i in range(0, instanceCount)])
			}))

		# Create a location block
		# Have to use a different template for root and non root webPath due to nginx quirks
		
		webPath = appInfo["webPath"].strip("/") # conf already has slashes
		
		if len(webPath) > 0: # Not root
			confLocationBlocks.append(fromTemplate("nginx-serverapp-location.template", {
				"###WEBPATH###" : webPath,
				"###UPSTREAM_NAME###" : upstreamName
			}))
		else:
			confLocationBlocks.append(fromTemplate("nginx-serverapp-root-location.template", {
				"###UPSTREAM_NAME###" : upstreamName
			}))


def addRedirectLocationBlock(redirectInfo, confLocationBlocks):
	if "regex" in redirectInfo:
		confLocationBlocks.append(fromTemplate("nginx-redirect-regex-location.template", {
			"###REGEX###" : redirectInfo["regex"],
			"###REDIRECT_CODE###" : str(redirectInfo.get("code", 301)),
			"###REDIRECT_URL###" : redirectInfo["destination"]
		}))
	else:
		confLocationBlocks.append(fromTemplate("nginx-redirect-location.template", {
			"###REDIRECT_CODE###" : str(redirectInfo.get("code", 301)),
			"###REDIRECT_URL###" : redirectInfo["destination"]
		}))


def buildNginxConf(newInstallDir, thingsByDomain, letsencryptThumbprint):
	confServerBlocks = []
	confUpstreamBlocks = []
	upstreamBlockNames = set()

	# Add a server block for each domain name
	# Each may in turn contain several apps
	for domain, things in thingsByDomain.items():
		appInfos = things["apps"]
		redirectInfos = things["redirects"]
		
		rootApp = None
		defaultRoot = "/var/www/html"
		confLocationBlocks = []

		for appInfo in appInfos: # For each app of this domain
			# There is a top level, root, app
			if appInfo["webPath"] == "/":
				rootApp = appInfo
			else:
				addAppLocationBlock(appInfo, upstreamBlockNames, confUpstreamBlocks, confLocationBlocks, newInstallDir)
		
		for redirectInfo in redirectInfos:
			addRedirectLocationBlock(redirectInfo, confLocationBlocks)
		
		# Add the root app last, so its regex location is matched last if other matches fail
		if rootApp:
			addAppLocationBlock(rootApp, upstreamBlockNames, confUpstreamBlocks, confLocationBlocks, newInstallDir)
			
			# Only add web root for a web app
			if appInfo["isWebApp"]:
				defaultRoot = getAppInstalledPath(newInstallDir, rootApp)

		confServerBlocks.append(fromTemplate("nginx-server-block.template", {
			"###SSL_CERT_FULLCHAIN###" : "/root/" + getCertFullchainPath(domain),
			"###SSL_CERT_KEY###" : "/root/" + getCertPrivkeyPath(domain),
			"###DEFAULT_ROOT###" : defaultRoot,
			"###DOMAIN_NAME###" : domain,
			"###APP_LOCATION_BLOCKS###" : "\n".join(confLocationBlocks)
		}))

	return fromTemplate("nginx-conf.template", {
		"###APP_UPSTREAM_BLOCKS###" : "\n".join(confUpstreamBlocks),
		"###LETSENCRYPT_ACCOUNT_THUMBPRINT###" : letsencryptThumbprint,
		"###SERVER_BLOCKS###" : "\n".join(confServerBlocks)
	})
