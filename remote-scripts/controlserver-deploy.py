import sys, json, asyncio
import constants
from utils import getProjectNameAndTarget, rsync, getDeploymentKey

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

with open(constants.DEPLOYMENTS_DIR + "/" + deploymentName + "/appcontrol.json") as fp:
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
    commands = []

    for host in hosts:
        commands.append( rsync(host, getDeploymentKey(deploymentName), "./", constants.SCRIPTS_DIR_NAME) )

    await asyncio.gather(*commands)

asyncio.run(deploy())
