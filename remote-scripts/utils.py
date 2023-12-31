import asyncio, sys, subprocess, json, os, re
from subprocess import CalledProcessError
from errors import HostVerificationError
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
		raise CalledProcessError(proc.returncode, argList[0], stdout.decode(), stderr.decode())

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

async def _rsyncNoRetry(host, keyPath, sourceDir, destDir, extraArgs = []):
	remoteShell = "ssh -oBatchMode=yes -i " + keyPath
	dest = "root@[" + host + "]:" + destDir;
	
	try:
		return await runCommandAsync([
				"rsync",
				"-rzl",
				"-e", remoteShell,
				"--delete",
				"--checksum",
				"--timeout=10",
				"--outbuf=L"
			]
			+ extraArgs
			+ [sourceDir, dest]
		)
	except CalledProcessError as error:
		if constants.HOST_VERIFICATION_MATCH_STR in error.stderr:
			raise HostVerificationError(host)
		else:
			raise error

# rsync with continuous retry for any CalledProcessError
async def rsync(host, keyPath, sourceDir, destDir, extraArgs = []):
	while True:
		try:
			await _rsyncNoRetry(host, keyPath, sourceDir, destDir, extraArgs)
			break
		except CalledProcessError as error:
			print(error)
			print(f"Rsync from master server to {host} failed with code {error.returncode}, will retry...");
			await asyncio.sleep(5)

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
