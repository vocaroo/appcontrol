import os
from utils import runCommand

class Runtime:
	# if version is given, will install that. Otherwise will install latest.
	def install(self, version = None):
		# Install nvm if not already
		if not os.path.isdir(".nvm"):
			runCommand(["curl", "-o", "nvm-install.sh", "https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.1/install.sh"])
			runCommand(["bash", "nvm-install.sh"])
		
		# Install a desired node version, if not already
		if version:
			if runCommand(["bash", "-i", "-c", "nvm", "which", str(version)], returnCode = True) != 0:
				runCommand(["bash", "-i", "-c", "nvm", "install", str(version)])
		else:
			# just ensure latest is installed
			runCommand(["bash", "-i", "-c", "nvm", "install", "node"])
	
	def getEnv(self, version = None):
		return {
			"NODE_ENV" : "production",
			"NODE_VERSION" : (version if version else "node") # Default to latest node if no version given
		}
	
	def getRunCommand(self, mainScriptPath, version = None):
		#return f"nvm run {version} {mainScriptPath}"
		return f"/root/.nvm/nvm-exec node {mainScriptPath}"
