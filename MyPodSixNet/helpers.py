from dataclasses import dataclass
from icecream import ic
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

@dataclass(unsafe_hash=True, eq=True, frozen=True)
class NetworkAddress:
    ip: str = "localhost"
    port: int = 1234

    def __repr__(self) -> str:
        return f"{self.ip}:{self.port}"
    
    def to_json(self):
        return {
            "ip": self.ip,
            "port": self.port
        }
    
    @classmethod
    def from_json(cls, data):
        return cls(data["ip"], int(data["port"]))
    
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