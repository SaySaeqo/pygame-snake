import asyncio
import json
from .address import NetworkAddress

class EndPoint:
    """
    wrapper for asyncio.Transport
    """
    
    END_SEQ = b"\0---\0"

    def __init__(self, transport: asyncio.Transport):
        self.transport = transport
        self.address = NetworkAddress.from_transport(transport) 

    def send(self, action: str, data = None):
        self.transport.write(json.dumps({
            "action": action,
            "data": data
        }).encode() + self.END_SEQ)

    def __del__(self):
        self.transport.close()