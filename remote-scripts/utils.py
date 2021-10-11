import asyncio, sys
import constants
from pssh.clients import ParallelSSHClient

def getProjectNameAndTarget(deploymentName):
    parts = deploymentName.rpartition("-")
    return (parts[0], parts[2])

def getDeploymentKey(deploymentName):
    return constants.CONTROLSERVER_DEPLOYMENTS_DIR + "/" + deploymentName + "/" + constants.CONTROL_KEY_NAME

async def runCommandAsync(argList):
    proc = await asyncio.create_subprocess_exec(*argList, stdout = asyncio.subprocess.PIPE, stderr = asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        print(stderr.decode().strip())
        raise RuntimeError("Command " + str(argList[0]) + " exited with non zero return code " + str(proc.returncode))

    return stdout.decode().strip()

async def rsync(host, keyPath, sourceDir, destDir, extraArgs = []):
    remoteShell = "ssh -oBatchMode=yes -i " + keyPath
    dest = "root@" + host + ":" + destDir;

    return await runCommandAsync([
            "rsync",
            "-rzl",
            "-e", remoteShell,
            "--delete",
            "--timeout=10"
        ]
        + extraArgs
        + [sourceDir, dest]
    )

# Run a script across *all* hosts
def runOnAllHosts(hosts, deploymentName, scriptName):
    # We might want timeout and retry in future, but let's see if it's actually necessary.
    # Since these connections are between remote servers it should be rare.
    client = ParallelSSHClient(hosts, pkey = constants.CONTROLSERVER_DEPLOYMENTS_DIR + "/" + deploymentName + "/control-key")
    outputs = client.run_command("python3 -B " + constants.SCRIPTS_DIR + "/" + scriptName)

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
        sys.exit(1)