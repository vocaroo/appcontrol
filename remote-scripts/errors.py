
class HostVerificationError(Exception):
    def __init__(self, host):
        self.host = host
        super().__init__(f"Host verification failed for host {host}")
