import os, asyncio
from datetime import datetime
import constants
from control_utils import (
	readServers, getCertPrivkeyPath, getCertFullchainPath, getDomainsInServer, runCommandOnAllHosts,
	getAllDeployments, hostsFromServers, hostFromServer
)
from utils import rsync, getDeploymentKey

print("Propagating SSL certs... " + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

deployments = getAllDeployments()

# This might do duplicate work if the same domain name is used on the same host by multiple deployments
# but that's probably okay... for now.
async def propagate():
	for deploymentName in deployments:
		servers = readServers(deploymentName)
		
		rsyncTasks = []
		
		for server in servers:
			host = hostFromServer(server)
			
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

async def reload_nginx():
	# Reload nginx config on each host so new cert is seen
	for deploymentName in deployments:
		print("Reloading nginx across deployment " + deploymentName)
		servers = readServers(deploymentName)
		hosts = hostsFromServers(servers)
		
		if not await runCommandOnAllHosts(hosts, deploymentName, "systemctl --no-block reload nginx"):
			print("Error, one or more nginx reload commands failed.")

asyncio.run(propagate())
asyncio.run(reload_nginx())
