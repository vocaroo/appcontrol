import sys
import constants
from utils import runCommand, ConfigStore

# A place to store some local state for control server
localConf = ConfigStore(constants.CONTROLSERVER_CONF_PATH)

print("Initialising control server...")

# Initial setup and install of some things on this master server
if localConf.get("setup") == None:
	runCommand(["apt", "update"])
	runCommand(["apt", "install", "-y", "python3-pip"])
	runCommand([sys.executable, "-m", "pip", "install", "parallel-ssh"])
	localConf.set("setup", True)
