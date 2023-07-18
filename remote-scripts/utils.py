import asyncio, sys, subprocess, json, os, re
import constants

def getProjectNameAndTarget(deploymentName):
	return re.match("^(.+)---(.+)$", deploymentName).groups()

def getDeploymentKey(deploymentName):
	return constants.CONTROLSERVER_DEPLOYMENTS_DIR + "/" + deploymentName + "/" + constants.CONTROL_KEY_NAME

def runCommand(args, addToEnv = None, returnCode = False):
	env = None

	if addToEnv:
		env = os.environ.copy()
		for key, value in addToEnv.items():
			env[key] = value

	completed = subprocess.run(args, stdout = subprocess.PIPE, stderr = subprocess.PIPE, env = env)
	
	if returnCode:
		return completed.returncode
	else:
		completed.check_returncode()
		return completed.stdout.decode("utf-8").strip()

async def runCommandAsync(argList):
	proc = await asyncio.create_subprocess_exec(*argList, stdout = asyncio.subprocess.PIPE, stderr = asyncio.subprocess.PIPE)
	stdout, stderr = await proc.communicate()

	if proc.returncode != 0:
		print(stderr.decode().strip())
		raise RuntimeError("Command " + str(argList[0]) + " exited with non zero return code " + str(proc.returncode))

	return stdout.decode().strip()

# Rsync between local directories, synchronously
def localRsync(sourceDir, destDir, extraArgs = []):
	return runCommand([
			"rsync",
			"-rzl",
			"--delete",
			"--checksum"
		]
		+ extraArgs
		+ [sourceDir, destDir]
	)

async def rsync(host, keyPath, sourceDir, destDir, extraArgs = []):
	remoteShell = "ssh -oBatchMode=yes -i " + keyPath
	dest = "root@[" + host + "]:" + destDir;

	return await runCommandAsync([
			"rsync",
			"-rzl",
			"-e", remoteShell,
			"--delete",
			"--checksum",
			"--timeout=10"
		]
		+ extraArgs
		+ [sourceDir, dest]
	)

# Simple on disk key-value store
class ConfigStore:
	def __init__(self, filePath):
		self.filePath = filePath

		try:
			with open(filePath) as f:
				self.data = json.load(f)
		except FileNotFoundError:
			self.data = {}

	def get(self, keyName, default = None):
		try:
			return self.data[keyName]
		except KeyError:
			return default

	def set(self, keyName, value):
		self.data[keyName] = value

		with open(self.filePath, "w") as f:
			json.dump(self.data, f)
