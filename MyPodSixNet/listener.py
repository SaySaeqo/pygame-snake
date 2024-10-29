from .endpoint import *
from .logger import LOG

class NetworkListener:
    def __init__(self, connection: EndPoint) -> None:
        self.conn = connection

    def Network_default(self, data):
        LOG.info("Event 'default' from" + str(self.conn.address))

    def Network(self, data):
        LOG.info("Network from" + str(self.conn.address))

    def Network_connected(self, data):
        LOG.info("Connected to " + str(self.conn.address))

    def Network_disconnected(self, data):
        LOG.info("Disconnected from" + str(self.conn.address))