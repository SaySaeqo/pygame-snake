import asyncio
from .endpoint import *
from .listener import *
from .address import *
import json


connections = {}
serving_task = None


class GeneralProtocol(asyncio.Protocol):
    
        def __init__(self, network_listener_factory):
            self.network_listener_factory = network_listener_factory
            pass
    
        def connection_made(self, transport: asyncio.Transport):
            self.transport = transport
            endpoint = EndPoint(transport)
            self.network_listener: NetworkListener = self.network_listener_factory(endpoint)
            self.network_listener.Network_connected()
            self.transport_address = NetworkAddress.from_transport(transport)
            global connections
            connections[self.transport_address] = (endpoint, self.network_listener)
    
        def data_received(self, data):
            for d in data.split(EndPoint.END_SEQ)[:-1]:
                d = json.loads(d.decode())
                handler_name = "Network_" + d["action"]
                if hasattr(self.network_listener, handler_name):
                    getattr(self.network_listener, handler_name)(d["data"])
                self.network_listener.Network(d)
    
        def connection_lost(self, exc):
            if exc:
                LOG.error("Connection lost due to error: {}".format(exc))
            self.network_listener.Network_disconnected()
            global connections
            try:
                del connections[self.transport_address]
            except KeyError:
                pass


async def connect_to_server(address: NetworkAddress, network_listener_factory = lambda conn: NetworkListener(conn)) -> EndPoint:
    loop = asyncio.get_running_loop()
    t, p = await loop.create_connection(lambda : GeneralProtocol(network_listener_factory), address.ip, address.port)
    
    return EndPoint(t)

async def start_server(address: NetworkAddress, network_listener_factory = lambda conn: NetworkListener(conn)):
    loop = asyncio.get_running_loop()
    server = await loop.create_server(lambda : GeneralProtocol(network_listener_factory), address.ip, address.port)
    global serving_task
    serving_task = asyncio.create_task(server.serve_forever())

def send(self, action: str, data = None, to: NetworkAddress = None):
    if to is None:
        [conn.send(action, data) for conn, _ in connections]
    else:
        connections[to][0].send(action, data)

def close():
    global connections
    for conn, _ in connections:
        conn.transport.close()
    connections.clear()
    global serving_task
    if serving_task:
        serving_task.cancel()
    serving_task = None