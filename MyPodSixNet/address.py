import re
from dataclasses import dataclass
import asyncio

@dataclass(unsafe_hash=True, eq=True, frozen=True)
class NetworkAddress:
    ip: str = "localhost"
    port: int = 1234

    def __repr__(self) -> str:
        return f"{self.ip}:{self.port}"
    
    @classmethod
    def from_transport(cls, transport: asyncio.Transport):
        host, ip = transport.get_extra_info('peername')[:2]
        if not re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", host):
            host = "localhost"
        return cls(host, ip)