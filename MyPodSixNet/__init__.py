from dataclasses import dataclass
import asyncio
import logging
from endpoint import EndPoint
from server import Server
from icecream import ic

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

@dataclass
class NetworkAddress:
    ip: str = "localhost"
    port: int = 1234

    def __repr__(self) -> str:
        return f"{self.ip}:{self.port}"
    
class NetworkListener:
    def __init__(self, address: NetworkAddress) -> None:
        self.address = address

    def Network_default(self, data):
        log.info("Event 'default'")
        ic(self.address, data)

    def Network(self, data):
        log.info("Network")
        ic(self.address, data)

    def Network_connected(self, data):
        log.info("Connected")
        ic(self.address, data)

    def Network_disconnected(self, data):
        log.info("Disconnected")
        ic(self.address, data)
    
async def connect_to_server(address: NetworkAddress, network_listener_factory = lambda address: NetworkListener(address)):

    reader, writer = await asyncio.open_connection(address.ip, address.port)
    connection = EndPoint(reader, writer, network_listener_factory)
    connection.start_listening()

    return connection

    # pamiętać o tym tutaj
    connection.writer.close()

async def start_server(address: NetworkAddress, network_listener_factory = lambda address: NetworkListener(address)):
    server = Server(address, network_listener_factory)
    await server.start()
    return server