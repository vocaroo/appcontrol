import json
import constants
from utils import getProjectNameAndTarget

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