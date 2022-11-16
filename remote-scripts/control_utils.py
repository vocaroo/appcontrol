import json, os, sys
import constants
from utils import getProjectNameAndTarget
from pssh.clients import ParallelSSHClient

def getCertPrivkeyPath(domain):
	return constants.CONTROLSERVER_CERTS_DIR + "/" + domain + ".key.pem"

def getCertFullchainPath(domain):
	return constants.CONTROLSERVER_CERTS_DIR + "/" + domain + ".fullchain.pem"

# Get the set of all domains used by an entire deployment (list of server definitions)
def getAllDomains(servers):
	domainSet = set()
	for server in servers:
		for appInfo in server["apps"]:
			if "domain" in appInfo:
				domainSet.add(appInfo["domain"])
	return domainSet

# Get set of domains required by a single server/host
def getDomainsInServer(server):
	domainSet = set()
	for appInfo in server["apps"]:
		if "domain" in appInfo:
			domainSet.add(appInfo["domain"])
	return domainSet

def readDeployConfigServers(deploymentName):
	projectName, deployTarget = getProjectNameAndTarget(deploymentName)
	
	with open(constants.CONTROLSERVER_DEPLOYMENTS_DIR + "/" + deploymentName + "/" + constants.LOCAL_CONFIG_FILE) as fp:
		deployConfig = json.load(fp)
		assert (deployTarget in deployConfig)
		servers = deployConfig[deployTarget]
	
	return (deployConfig, servers)

def getAllDeployments():
	return os.listdir(constants.CONTROLSERVER_DEPLOYMENTS_DIR)

# Get all server blocks from all deployments
def getAllDeploymentServers():
	allServers = []
	deployments = getAllDeployments()
	
	for deploymentName in deployments:
		deployConfig, servers = readDeployConfigServers(deploymentName)		
		allServers.extend(servers)
	
	return allServers

# Write correct host fingerprints to known_hosts
# This must be done for *all* deployments on this control server, not just the one that is currently being deployed.
def writeKnownHosts():
	servers = getAllDeploymentServers()
	
	with open(constants.KNOWN_HOSTS_PATH, "w") as fp:
		for server in servers:
			assert ("fingerprint" in server and len(server["fingerprint"]) > 0), "No fingerprint in server block"
			fp.write(server["ip"] + " ssh-ed25519 " + server["fingerprint"] + "\n")

def runCommandOnAllHosts(hosts, deploymentName, commandStr):
	# We might want timeout and retry in future, but let's see if it's actually necessary.
	# Since these connections are between remote servers it should be rare.
	client = ParallelSSHClient(hosts, pkey = constants.CONTROLSERVER_DEPLOYMENTS_DIR + "/" + deploymentName + "/control-key")
	outputs = client.run_command(commandStr)

	client.join()

	failed = False

	for output in outputs:
		if output.exit_code != 0:
			print("Server command failed.")
			print("Command exit code: " + str(output.exit_code))
			print("Command stdout: " + "".join(output.stdout))
			print("Command stderr: " + "".join(output.stderr))
			failed = True

	if failed:
		print("One or more server commands failed.")
		return False
	
	return True

# Run a script across *all* hosts
# Also exits if anything fails, this is currently assumed to only be used by deploy script
def runOnAllHosts(hosts, deploymentName, scriptName):
	if not runCommandOnAllHosts(hosts, deploymentName, "python3 -B " + constants.HOSTSERVER_SCRIPTS_DIR + "/" + scriptName):
		sys.exit(1)
