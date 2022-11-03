import os
from utils import runCommand

N_PATH = "/usr/local/bin/n"

class Runtime:
	# if version is given, will install that. Otherwise if None, will install latest.
	def install(self, version):
				
		# Install n if not already
		if not os.path.isdir(N_PATH):
			runCommand(["curl", "-L", "https://raw.githubusercontent.com/tj/n/master/bin/n", "-o", N_PATH])
			os.chmod(N_PATH, 0o755)
		
		# Install a desired node version, if not already
		if version:
			if runCommand(["n", "which", str(version)], returnCode = True) != 0:
				runCommand(["n", "install", str(version)])
		else:
			# just ensure latest is installed
			runCommand(["n", "install", "latest"])
	
	def getEnv(self, version):
		return {
			"NODE_ENV" : "production"
		}
	
	def getRunCommand(self, mainScriptPath, version):
		if version == None:
			version = "latest"
		
		return f"n run {version} {mainScriptPath}"
