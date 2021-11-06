import sys, json, asyncio, os, re
import constants
from utils import getProjectNameAndTarget, rsync, getDeploymentKey, runOnAllHosts, runCommand, ConfigStore

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

with open(constants.CONTROLSERVER_DEPLOYMENTS_DIR + "/" + deploymentName + "/appcontrol.json") as fp:
	deployConfig = json.load(fp)
	assert (deployTarget in deployConfig)

	servers = deployConfig[deployTarget]
	letsencryptConfig = deployConfig["letsencrypt"]
	hosts = [server["ip"] for server in servers]

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
	print( runCommand([ACME_SH_PATH, "--register-account"]) )

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

def getAllDomains(servers):
	domainSet = set()
	for server in servers:
		for appInfo in server["apps"]:
			if "domain" in appInfo:
				domainSet.add(appInfo["domain"])
	return domainSet

domainSet = getAllDomains(servers)

print("All domains in this deployment:", str(domainSet))

# Issue certs!!

def getCertPrivkeyPath(domain):
	return constants.CONTROLSERVER_CERTS_DIR + "/" + domain + ".key.pem"

def getCertFullchainPath(domain):
	return constants.CONTROLSERVER_CERTS_DIR + "/" + domain + ".fullchain.pem"

def issueCerts(domainSet):
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

		# Install the certs to another directory
		print(runCommand([
			ACME_SH_PATH, "--install-cert", "-d", domain,
			"--key-file", getCertPrivkeyPath(domain),
			"--fullchain-file", getCertFullchainPath(domain)
		]))

# Issue certs for those that have not already been issued (check for existance of cert)

domainsWithoutCerts = [domain for domain in domainSet if not os.path.isfile(getCertFullchainPath(domain))]

if len(domainsWithoutCerts) > 0:
	print("Issuing certs for the following domains", str(domainsWithoutCerts))
	issueCerts(domainsWithoutCerts)

# Now want to rsync to each host!
async def deploy():
	# Sync all the control scripts
	await asyncio.gather(*[
		rsync(host, getDeploymentKey(deploymentName), constants.CONTROLSERVER_SCRIPTS_DIR + "/", constants.SCRIPTS_DIR) for host in hosts
	])

	# Run server-init.py on each. Creates some necessary dirs and installs some stuff if not already installed
	runOnAllHosts(hosts, deploymentName, "host-init.py " + deploymentName)

	# Sync all apps for each deployment
	await asyncio.gather(*[
		rsync(host, getDeploymentKey(deploymentName),
			constants.CONTROLSERVER_DEPLOYMENTS_DIR + "/" + deploymentName + "/apps/",
			constants.DEPLOYMENTS_DIR + "/" + deploymentName + "/"
		) for host in hosts
	])

	# Install all apps
	runOnAllHosts(hosts, deploymentName, "host-install-apps.py")

asyncio.run(deploy())
