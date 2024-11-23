from .address import *
from .logger import LOG

class NetworkListener:
    def __init__(self, address: NetworkAddress) -> None:
        self.address = address

    def Network_default(self, data):
        LOG.debug("Event 'default' from " + str(self.address))

    def Network(self, data):
        LOG.debug(f"Action {data['action']} from " + str(self.address))

    def Network_connected(self):
        LOG.debug("Connected to " + str(self.address))

    def Network_disconnected(self):
        LOG.debug("Disconnected from " + str(self.address))