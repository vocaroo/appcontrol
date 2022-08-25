from host_utils import fromTemplate, getAppInstalledPath, getCertPrivkeyPath, getCertFullchainPath

def buildNginxConf(newInstallDir, appsByDomain):
	confServerBlocks = []
	confUpstreamBlocks = []

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
						"###ROOT_DIR###" : getAppInstalledPath(newInstallDir, appInfo)
					}))
				else: # Server app
					# Create an upstream block

					upstreamName = appInfo["deploymentName"] + "-" + appInfo["appName"]
					# Default to just one instance in total if "instancesPerCPU" is set to zero (the default)
					# Otherwise... an instance per CPU!
					instanceCount = appInfo["instanceCount"]

					confUpstreamBlocks.append(fromTemplate("nginx-serverapp-upstream.template", {
						"###UPSTREAM_NAME###" : upstreamName,
						"###SERVERS###" : "\n"
							.join(["server 127.0.0.1:" + str(appInfo["portRangeStart"] + i) + " max_fails=0;" for i in range(0, instanceCount)])
					}))

					# Create a location block
					confLocationBlocks.append(fromTemplate("nginx-serverapp-location.template", {
						"###WEBPATH###" : appInfo["webPath"].strip("/"), # conf already has slashes
						"###UPSTREAM_NAME###" : upstreamName
					}))

		if rootApp:
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
		"###SERVER_BLOCKS###" : "\n".join(confServerBlocks)
	})