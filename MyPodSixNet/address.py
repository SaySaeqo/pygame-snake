import re
from dataclasses import dataclass

@dataclass(unsafe_hash=True, eq=True, frozen=True)
class NetworkAddress:
    ip: str = "localhost"
    port: int = 1234

    def corrected_ip(self):
        if not re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", self.ip):
            return "localhost"
        return self.ip

    def __repr__(self) -> str:
        return f"{self.corrected_ip()}:{self.port}"
    
    def to_json(self):
        return {
            "ip": self.ip,
            "port": self.port
        }
    
    @classmethod
    def from_json(cls, data):
        return cls(data["ip"], int(data["port"]))