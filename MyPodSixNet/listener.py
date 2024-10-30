from .endpoint import *
from .logger import LOG

class NetworkListener:
    def __init__(self, connection: EndPoint) -> None:
        self.conn = connection

    def Network_default(self, data):
        LOG.debug("Event 'default' from " + str(self.conn.address))

    def Network(self, data):
        LOG.debug(f"Action {data['action']} from " + str(self.conn.address))

    def Network_connected(self, data):
        LOG.debug("Connected to " + str(self.conn.address))

    def Network_disconnected(self, data):
        LOG.debug("Disconnected from " + str(self.conn.address))