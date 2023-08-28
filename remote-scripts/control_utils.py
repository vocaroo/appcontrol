import json, os, sys, asyncio
import constants
import asyncssh
from utils import getProjectNameAndTarget

def getCertPrivkeyPath(domain):
	return constants.CONTROLSERVER_CERTS_DIR + "/" + domain + ".key.pem"

def getCertFullchainPath(domain):
	return constants.CONTROLSERVER_CERTS_DIR + "/" + domain + ".fullchain.pem"

# Get the set of all domains used by an entire deployment (list of server definitions)
def getAllDomains(servers):
	domainSet = set()
	
	for server in servers:
		domainSet.update(getDomainsInServer(server))
	
	return domainSet

# Get set of domains required by a single server/host
def getDomainsInServer(server):
	domainSet = set()
	
	if "apps" in server:
		for appInfo in server["apps"]:
			if "domains" in appInfo:
				for domain in appInfo["domains"]:
					domainSet.add(domain)
	
	if "redirects" in server:
		for redirect in server["redirects"]:
			if "domain" in redirect:
				domainSet.add(redirect["domain"])

	return domainSet

def readDeployConfigFromDir(deploymentName, dirPath):
	with open(dirPath + "/" + deploymentName + "/" + constants.LOCAL_CONFIG_FILE) as fp:
		return json.load(fp)

# Return the deploy config for a given deployment
def readDeployConfig(deploymentName):
	return readDeployConfigFromDir(deploymentName, constants.CONTROLSERVER_DEPLOYMENTS_DIR)

def serversFromDeployConfig(deploymentName, deployConfig):
	projectName, deployTarget = getProjectNameAndTarget(deploymentName)
	assert ("deployment" in deployConfig)
	return deployConfig["deployment"]["servers"]

# Read only the servers from a deployment
def readServers(deploymentName):
	return serversFromDeployConfig(deploymentName, readDeployConfig(deploymentName))

# Read the servers from an incoming deployment (from the temporary -incoming directory)
def readServersIncoming(deploymentName):
	return serversFromDeployConfig(deploymentName, readDeployConfigFromDir(deploymentName, constants.CONTROLSERVER_DEPLOYMENTS_INCOMING_DIR))

def getAllDeployments():
	return os.listdir(constants.CONTROLSERVER_DEPLOYMENTS_DIR)

# Get all server blocks from all deployments
def getAllDeploymentServers():
	allServers = []
	deployments = getAllDeployments()
	
	for deploymentName in deployments:
		allServers.extend(readServers(deploymentName))
	
	return allServers

def getServersByHost(servers): # group by IP
	serversByHost = {}
	
	for server in servers:
		host = hostFromServer(server)
		
		if host in serversByHost:
			serversByHost[host].append(server)
		else:
			serversByHost[host] = [server]
	
	return serversByHost

def hostFromServer(server):
	assert("ipv6" in server or "ipv4" in server)
	
	if "ipv6" in server:
		return server["ipv6"]
	else:
		return server["ipv4"]

def hostsFromServers(servers):
	return [hostFromServer(server) for server in servers]

# Write correct host fingerprints to known_hosts
# This must be done for *all* deployments on this control server, not just the one that is currently being deployed.
def writeKnownHosts():
	servers = getAllDeploymentServers()
	
	with open(constants.KNOWN_HOSTS_PATH, "w") as fp:
		for server in servers:
			assert ("fingerprint" in server and len(server["fingerprint"]) > 0), "No fingerprint in server block"
			if "ipv4" in server:
				fp.write(server["ipv4"] + " ssh-ed25519 " + server["fingerprint"] + "\n")
			if "ipv6" in server:
				fp.write(server["ipv6"] + " ssh-ed25519 " + server["fingerprint"] + "\n")

async def _runCommandOnHostNoRetry(host, deploymentName, commandStr):
	keyPath = constants.CONTROLSERVER_DEPLOYMENTS_DIR + "/" + deploymentName + "/control-key"
	
	async with asyncssh.connect(host, client_keys = [keyPath]) as conn:
		result = await conn.run(commandStr)
		
		if result.returncode != 0:
			print("Server command failed.")
			print("Command exit code: " + str(result.returncode))
			print("Command stdout: " + "".join(result.stdout))
			print("Command stderr: " + "".join(result.stderr))
			return False
		
		return True

async def runCommandOnHost(host, deploymentName, commandStr):
	while True:
		try:
			return await _runCommandOnHostNoRetry(host, deploymentName, commandStr)
		except Exception as error:
			print(error)
			print(commandStr)
			print(f"Master server failed to run command on {host}, will retry...");
			await asyncio.sleep(5)

async def runCommandOnAllHosts(hosts, deploymentName, commandStr):
	results = await asyncio.gather(*[runCommandOnHost(host, deploymentName, commandStr) for host in hosts])
	allSucceeded = all(results)
	
	if not allSucceeded:
		print("One or more server commands failed.")
	
	# Return true if ALL commands succeeded, false if any failed
	return allSucceeded

# Run a script across *all* hosts
# Also exits if anything fails, this is currently assumed to only be used by deploy script
async def runOnAllHosts(hosts, deploymentName, scriptName):
	if not await runCommandOnAllHosts(hosts, deploymentName, f"python3 -B -u {constants.HOSTSERVER_SCRIPTS_DIR}/{scriptName}"):
		sys.exit(constants.REMOTE_EXIT_CODE_HOST_COMMAND_FAILED)
