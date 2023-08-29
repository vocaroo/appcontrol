from pathlib import Path
import constants
from utils import runCommand

# This script is run on both control and host servers
# It may be run multiple times.

Path(constants.SSHD_CONFIG_PATH).write_text("""
LoginGraceTime 20s
MaxStartups 5:50:60
PasswordAuthentication no
""")

# Reload sshd
runCommand(["systemctl", "--no-block", "reload", "sshd"])
