import os, asyncio
from datetime import datetime
import constants
from control_utils import readDeployConfigServers, getCertPrivkeyPath, getCertFullchainPath, getDomainsInServer
from utils import rsync, getDeploymentKey, runCommandOnAllHosts, hostsFromServers

print("Propagating SSL certs... " + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

deployments = os.listdir(constants.CONTROLSERVER_DEPLOYMENTS_DIR)

# This might do duplicate work if the same domain name is used on the same host by multiple deployments
# but that's probably okay... for now.
async def propagate():
	for deploymentName in deployments:
		deployConfig, servers = readDeployConfigServers(deploymentName)
		
		rsyncTasks = []
		
		for server in servers:
			host = server["ip"]
			
			for domainName in getDomainsInServer(server):
				print("Propagating " + domainName + " keys to host " + host)
				
				rsyncTasks.append(rsync(host, getDeploymentKey(deploymentName),
					getCertPrivkeyPath(domainName),
					constants.HOSTSERVER_CERTS_DIR + "/"
				))
				rsyncTasks.append(rsync(host, getDeploymentKey(deploymentName),
					getCertFullchainPath(domainName),
					constants.HOSTSERVER_CERTS_DIR + "/"
				))
		
		await asyncio.gather(*rsyncTasks)

asyncio.run(propagate())

# Reload nginx config on each host so new cert is seen
# This is blocking per deployment, could be improved
for deploymentName in deployments:
	print("Reloading nginx across deployment " + deploymentName)
	deployConfig, servers = readDeployConfigServers(deploymentName)
	hosts = hostsFromServers(servers)
	
	if not runCommandOnAllHosts(hosts, deploymentName, "systemctl --no-block reload nginx"):
		print("Error, one or more reload commands failed.")
