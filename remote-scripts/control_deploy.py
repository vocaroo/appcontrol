import sys, json, asyncio, os, re, tempfile, shutil
import constants
from utils import getProjectNameAndTarget, rsync, getDeploymentKey, runOnAllHosts, runCommand, ConfigStore, hostsFromServers
from control_utils import readDeployConfigServers, getCertPrivkeyPath, getCertFullchainPath, getAllDomains, getDomainsInServer

ACME_SH_PATH = "/root/.acme.sh/acme.sh"

print("Initialising control server...")

deploymentName = sys.argv[1]
assert(len(deploymentName) > 0)

# e.g. MyProject, production
projectName, deployTarget = getProjectNameAndTarget(deploymentName)

print("Deploying from control server...")
print("full deployment name:", deploymentName)
print("projectName:", projectName)
print("deployTarget:", deployTarget)

os.makedirs(constants.CONTROLSERVER_CERTS_DIR, exist_ok = True)

# A place to store some local state for control server
localConf = ConfigStore(constants.CONTROLSERVER_CONF_PATH)

# Must deploy scripts (from working directory) to all other servers in this deploy target (to their local ~/appcontrol dir)
# First, get the host IPs
deployConfig, servers = readDeployConfigServers(deploymentName)
hosts = hostsFromServers(servers)

# Write cron job to propagate certs
def writeCertPropagationCron():
	cronFilePath = "/etc/cron.daily/" + constants.TOOL_NAME_LOWERCASE + "-propagate-certs"
	
	with open(cronFilePath, "w") as fp:
		certPropagateScriptPath = constants.CONTROLSERVER_SCRIPTS_DIR + "/control_propagate_certs.py"
		fp.write("#!/bin/sh\ncd /root && python3 " + certPropagateScriptPath + " >> /var/log/" + constants.TOOL_NAME_LOWERCASE + "-propagate-certs.log")
	
	os.chmod(cronFilePath, 0o755)

writeCertPropagationCron()

print("Deploying to hosts", hosts)

# Write correct host fingerprints to known_hosts
with open(constants.KNOWN_HOSTS_PATH, "w") as fp:
	for server in servers:
		assert ("fingerprint" in server and len(server["fingerprint"]) > 0), "No fingerprint in server block"
		fp.write(server["ip"] + " ssh-ed25519 " + server["fingerprint"] + "\n")

email = deployConfig["email"]

# Install and set up acme.sh if not already
if not os.path.isdir(".acme.sh"):
	print("Installing acme.sh")
	print( runCommand(["wget", "-O", "/tmp/acme.sh", "https://raw.githubusercontent.com/acmesh-official/acme.sh/master/acme.sh"]) )
	print( runCommand(["sh", "/tmp/acme.sh", "--install-online", "-m", email]) )
	assert os.path.isdir(".acme.sh")
	print( runCommand([ACME_SH_PATH, "--set-default-ca", "--server", "letsencrypt"]) )
	registerAccountStdout = runCommand([ACME_SH_PATH, "--register-account"])
	print( registerAccountStdout )
	thumbprint = re.search(r"ACCOUNT_THUMBPRINT='([-_a-zA-Z0-9]+)'", registerAccountStdout).group(1)
	print(f"Letsencrypt account thumbprint [{thumbprint}]")
	# Save letsencrypt account thumbprint
	localConf.set("letsencryptThumbprint", thumbprint)

assert localConf.get("letsencryptThumbprint"), "No letsencrypt thumbprint found"

# Update letsencrypt account email if it has changed
if email != localConf.get("email"):
	print("Email changed from " + str(localConf.get("email")) + " to " + email + ", setting new letsencrypt email...")
	runCommand([ACME_SH_PATH, "-m", email, "--update-account"])
	localConf.set("email", email)

# One further question --- Do we need to define control server separate from appcontrol.json ??? Like email and stuff... IP and fingerprint....????
# A "default_group" that contains email in user dir (~/.appcontrol/default_group)
# * Issue all necessary SSL certs here on control server (get set of all domains from deployment)
#       acme.sh --issue -d appcontrol-testapp-client-staging.xzist.org --stateless

# Get all domains for this deployment

domainSet = getAllDomains(servers)

print("All domains in this deployment:", str(domainSet))

def issueCertsDNS(domainSet):
	letsencryptConfig = deployConfig["letsencrypt"]
	dnsHookName = letsencryptConfig["dns_hook"]
	challengeAliasDomain = letsencryptConfig.get("challenge_alias_domain") # Can be omitted, so will be None

	acmeShIssueCommand = [ACME_SH_PATH, "--issue", "--dns", dnsHookName]

	if challengeAliasDomain:
		acmeShIssueCommand.extend(["--challenge-alias", challengeAliasDomain])

	for domain in domainSet:
		# Issue cert for each domain separately
		acmeShIssueCommandForThisDomain = acmeShIssueCommand + ["-d", domain]

		print(acmeShIssueCommandForThisDomain)
		print(runCommand(acmeShIssueCommandForThisDomain, letsencryptConfig["env"]))

		# Install the certs to appcontrol-master-certs dir
		print(runCommand([
			ACME_SH_PATH, "--install-cert", "-d", domain,
			"--key-file", getCertPrivkeyPath(domain),
			"--fullchain-file", getCertFullchainPath(domain)
		]))

def issueCertsHTTP(domainSet):
	acmeShIssueCommand = [ACME_SH_PATH, "--issue", "--stateless"]
	
	for domain in domainSet:
		# Issue cert for each domain separately
		acmeShIssueCommandForThisDomain = acmeShIssueCommand + ["-d", domain]

		print(acmeShIssueCommandForThisDomain)
		print(runCommand(acmeShIssueCommandForThisDomain))

		# Install the certs to appcontrol-master-certs dir
		print(runCommand([
			ACME_SH_PATH, "--install-cert", "-d", domain,
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
