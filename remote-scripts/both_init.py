from pathlib import Path
import constants
from utils import runCommand

# This script is run on both control and host servers
# It may be run multiple times.

Path(constants.SSHD_CONFIG_PATH).write_text("""
LoginGraceTime 20s
MaxStartups 5:50:60
PasswordAuthentication no

# https://www.ssh-audit.com/hardening_guides.html#ubuntu_22_04_lts
KexAlgorithms sntrup761x25519-sha512@openssh.com,curve25519-sha256,curve25519-sha256@libssh.org,gss-curve25519-sha256-,diffie-hellman-group16-sha512,gss-group16-sha512-,diffie-hellman-group18-sha512,diffie-hellman-group-exchange-sha256
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com,aes256-ctr,aes192-ctr,aes128-ctr
MACs hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com,umac-128-etm@openssh.com
HostKeyAlgorithms ssh-ed25519,ssh-ed25519-cert-v01@openssh.com,sk-ssh-ed25519@openssh.com,sk-ssh-ed25519-cert-v01@openssh.com,rsa-sha2-512,rsa-sha2-512-cert-v01@openssh.com,rsa-sha2-256,rsa-sha2-256-cert-v01@openssh.com
""")

# Reload sshd
runCommand(["systemctl", "--no-block", "reload", "sshd"])
