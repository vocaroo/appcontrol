import sys, json, asyncio
import constants
from utils import getProjectNameAndTarget, rsync, getDeploymentKey, runOnAllHosts

print("Initialising control server...")

deploymentName = sys.argv[1]
assert(len(deploymentName) > 0)

# e.g. MyProject, production
projectName, deployTarget = getProjectNameAndTarget(deploymentName)

print("Deploying from control server...")
print("full deployment name:", deploymentName)
print("projectName:", projectName)
print("deployTarget:", deployTarget)

# Must deploy scripts (from working directory) to all other servers in this deploy target (to their local ~/appcontrol dir)
# First, get the host IPs

with open(constants.CONTROLSERVER_DEPLOYMENTS_DIR + "/" + deploymentName + "/appcontrol.json") as fp:
    deployConfig = json.load(fp)
    assert (deployTarget in deployConfig)

    servers = deployConfig[deployTarget]
    hosts = [server["ip"] for server in servers]

print("Deploying to hosts", hosts)

# Write correct host fingerprints to known_hosts
with open(constants.KNOWN_HOSTS_PATH, "w") as fp:
    for server in servers:
        assert ("fingerprint" in server and len(server["fingerprint"]) > 0), "No fingerprint in server block"
        fp.write(server["ip"] + " ssh-ed25519 " + server["fingerprint"] + "\n")

# Now want to rsync to each host!
async def deploy():
    # Sync all the control scripts
    await asyncio.gather(*[
        rsync(host, getDeploymentKey(deploymentName), constants.CONTROLSERVER_SCRIPTS_DIR + "/", constants.SCRIPTS_DIR) for host in hosts
    ])

    # Run server-init.py on each. Creates some necessary dirs and installs some stuff if not already installed
    runOnAllHosts(hosts, deploymentName, "server-init.py " + deploymentName)

    # Sync all apps for each deployment
    await asyncio.gather(*[
        rsync(host, getDeploymentKey(deploymentName),
            constants.CONTROLSERVER_DEPLOYMENTS_DIR + "/" + deploymentName + "/apps/",
            constants.DEPLOYMENTS_DIR + "/" + deploymentName + "/"
        ) for host in hosts
    ])

asyncio.run(deploy())
