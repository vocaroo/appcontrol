import asyncio
import constants

def getProjectNameAndTarget(deploymentName):
    parts = deploymentName.rpartition("-")
    return (parts[0], parts[2])

def getDeploymentKey(deploymentName):
    return constants.DEPLOYMENTS_DIR + "/" + deploymentName + "/" + constants.CONTROL_KEY_NAME

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
