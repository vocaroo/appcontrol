import sys, json, asyncio, os, tempfile, shutil
import constants
from utils import ConfigStore

# A place to store some local state for control server
localConf = ConfigStore(constants.CONTROLSERVER_CONF_PATH)
# Check this before we import anything that uses non-standard modules (i.e. parallel-ssh)
assert localConf.get("initialised") != None, "Control server was not correctly initialised. Perhaps the reset command needs to be called."

from utils import getProjectNameAndTarget, rsync, getDeploymentKey, runCommand, hostsFromServers, localRsync
from control_utils import readDeployConfig, serversFromDeployConfig, getCertPrivkeyPath, getCertFullchainPath, getAllDomains, getDomainsInServer, runOnAllHosts, writeKnownHosts, getServersByHost, readServers, readServersIncoming, getAllDeployments

email = sys.argv[1]
deploymentName = sys.argv[2]
assert(len(email) > 0)
assert(len(deploymentName) > 0)

# e.g. MyProject, production
projectName, deployTarget = getProjectNameAndTarget(deploymentName)

print("Deploying from control server...")
print("full deployment name:", deploymentName)
print("projectName:", projectName)
print("deployTarget:", deployTarget)

# Update letsencrypt account email if it has changed
if email != localConf.get("email"):
	print("Email changed from " + str(localConf.get("email")) + " to " + email + ", setting new letsencrypt email...")
	runCommand([constants.ACME_SH_PATH, "-m", email, "--update-account"])
	localConf.set("email", email)

# Check for conflicts of web path - a given host cannot have a domain and web path served by more than one app
def checkForWebPathConflicts():
	# We want a list of all servers across all deployments that will exist *if* this deploy goes ahead
	newServersState = []
	
	# Find all servers from existing deployments, EXCLUDING this current deployment
	deploymentNames = getAllDeployments()
	
	for iterDeploymentName in deploymentNames:
		if iterDeploymentName != deploymentName:
			newServersState.extend(readServers(iterDeploymentName))
	
	# Then, also read the INCOMING servers of this new deployment
	newServersState.extend(readServersIncoming(deploymentName))
	
	# Organise all these servers by host IP
	serversByHost = getServersByHost(newServersState)
	
	# For each host IP
	for host, servers in serversByHost.items():
		domainAndWebPathSet = set()
		
		for server in servers:
			for appInfo in server["apps"]:
				domain = appInfo.get("domain", None)
				webPath = appInfo.get("webPath", "/")
				
				if domain:
					hash = domain + webPath
					
					if hash in domainAndWebPathSet:
						print("Same domain and webPath used in more than one app on the same server.")
						print(hash)
						print("Deployment aborted.")
						print("Please fix the problem and re-deploy.")						
						sys.exit(1)
					
					domainAndWebPathSet.add(hash)

checkForWebPathConflicts()

# Move incoming deployment to the *actual* deployment dir, now that some stuff above was validated
localRsync(
	constants.CONTROLSERVER_DEPLOYMENTS_INCOMING_DIR + "/" + deploymentName + "/",
	constants.CONTROLSERVER_DEPLOYMENTS_DIR + "/" + deploymentName,
)

# Must deploy scripts (from working directory) to all other servers in this deploy target (to their local ~/appcontrol dir)
# First, get the host IPs
deployConfig = readDeployConfig(deploymentName)
servers = serversFromDeployConfig(deploymentName, deployConfig)
hosts = hostsFromServers(servers)

print("Deploying to hosts", hosts)

# Write correct host fingerprints to known_hosts, for *all* deployments on this control server
writeKnownHosts()

# Issue all necessary SSL certs here on control server (get set of all domains from deployment)
# Get all domains for this deployment

domainSet = getAllDomains(servers)

print("All domains in this deployment:", str(domainSet))

def issueCertsDNS(domainSet):
	letsencryptConfig = deployConfig["letsencrypt"]
	dnsHookName = letsencryptConfig["dns_hook"]
	challengeAliasDomain = letsencryptConfig.get("challenge_alias_domain") # Can be omitted, so will be None

	acmeShIssueCommand = [constants.ACME_SH_PATH, "--issue", "--dns", dnsHookName]

	if challengeAliasDomain:
		acmeShIssueCommand.extend(["--challenge-alias", challengeAliasDomain])

	for domain in domainSet:
		# Issue cert for each domain separately
		acmeShIssueCommandForThisDomain = acmeShIssueCommand + ["-d", domain]

		print(acmeShIssueCommandForThisDomain)
		print(runCommand(acmeShIssueCommandForThisDomain, letsencryptConfig["env"]))

		# Install the certs to appcontrol-master-certs dir
		print(runCommand([
			constants.ACME_SH_PATH, "--install-cert", "-d", domain,
			"--key-file", getCertPrivkeyPath(domain),
			"--fullchain-file", getCertFullchainPath(domain)
		]))

def issueCertsHTTP(domainSet):
	acmeShIssueCommand = [constants.ACME_SH_PATH, "--issue", "--stateless"]
	
	for domain in domainSet:
		# Issue cert for each domain separately
		acmeShIssueCommandForThisDomain = acmeShIssueCommand + ["-d", domain]

		print(acmeShIssueCommandForThisDomain)
		print(runCommand(acmeShIssueCommandForThisDomain))

		# Install the certs to appcontrol-master-certs dir
		print(runCommand([
			constants.ACME_SH_PATH, "--install-cert", "-d", domain,
			"--key-file", getCertPrivkeyPath(domain),
			"--fullchain-file", getCertFullchainPath(domain)
		]))

def issueCerts(domainSet):
	if "letsencrypt" in deployConfig and "dns_hook" in deployConfig["letsencrypt"]:
		issueCertsDNS(domainSet)
	else:
		issueCertsHTTP(domainSet)

async def main():
	await initHosts()
	
	# Issue certs for those that have not already been issued (check for existance of cert)
	# Must initHosts above first to set up nginx to handle letsencrypt challenge
	domainsWithoutCerts = [domain for domain in domainSet if not os.path.isfile(getCertFullchainPath(domain))]

	if len(domainsWithoutCerts) > 0:
		print("Issuing certs for the following domains", str(domainsWithoutCerts))
		issueCerts(domainsWithoutCerts)
	
	await deploy()

async def initHosts():
	# Sync all the control scripts to *all* hosts
	await asyncio.gather(*[
		rsync(host, getDeploymentKey(deploymentName), constants.CONTROLSERVER_SCRIPTS_DIR + "/", constants.HOSTSERVER_SCRIPTS_DIR) for host in hosts
	])

	# Run server-init.py on each. Creates some necessary dirs and installs some stuff if not already installed
	runOnAllHosts(hosts, deploymentName, "host_init.py " + deploymentName + " " + localConf.get("letsencryptThumbprint"))

# Now want to rsync to each host!
async def deploy():
	# Now sync *ONLY* the desired apps and their SSL certs to each host
	rsyncTasks = []
	tempDirs = []

	for server in servers:
		host = server["ip"]
		
		tempDir = tempfile.TemporaryDirectory()
		tempDirs.append(tempDir)

		# Copy all apps for this server and deployment to a temp dir
		for appInfo in server["apps"]:
			appName = appInfo["app"]
			appTempDir = tempDir.name + "/" + appName

			shutil.copytree(
				constants.CONTROLSERVER_DEPLOYMENTS_DIR + "/" + deploymentName + "/apps/" + appName,
				appTempDir
			)

			# Inject some stuff that's needed by the host server into the app's appMeta.json
			with open(appTempDir + "/appMeta.json", "r+") as fp:
				appMeta = json.load(fp)
				appMeta["appName"] = appName
				appMeta["deploymentName"] = deploymentName

				# Copy certain keys from appInfo/config only if set
				for keyName in ["domain", "webPath", "instancesPerCPU", "dataGroup"]:
					if keyName in appInfo:
						appMeta[keyName] = appInfo[keyName]

			with open(appTempDir + "/appMeta.json", "w") as fp:
				json.dump(appMeta, fp, indent = "\t")

		# Rsync the apps to the host
		# This will also clear any apps that exist there and are no longer specified in the deployment
		rsyncTasks.append(rsync(host, getDeploymentKey(deploymentName),
			tempDir.name + "/",
			constants.HOSTSERVER_APPS_DIR + "/" + deploymentName + "/"
		))

		for domainName in getDomainsInServer(server):
			rsyncTasks.append(rsync(host, getDeploymentKey(deploymentName),
				getCertPrivkeyPath(domainName),
				constants.HOSTSERVER_CERTS_DIR + "/"
			))
			rsyncTasks.append(rsync(host, getDeploymentKey(deploymentName),
				getCertFullchainPath(domainName),
				constants.HOSTSERVER_CERTS_DIR + "/"
			))

	await asyncio.gather(*rsyncTasks)

	# Clean up tempdirs only after rsyncs have finished
	for tempDir in tempDirs:
		tempDir.cleanup()

	# Install all apps
	runOnAllHosts(hosts, deploymentName, "host_install_apps.py " + localConf.get("letsencryptThumbprint"))

asyncio.run(main())
