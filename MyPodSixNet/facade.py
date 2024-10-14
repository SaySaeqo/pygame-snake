import asyncio
from endpoint import *
from server import *
from listener import *
from address import *
    
async def connect_to_server(address: NetworkAddress, network_listener_factory = lambda address: NetworkListener(address)) -> EndPoint:
    reader, writer = await asyncio.open_connection(address.ip, address.port)
    connection = EndPoint(reader, writer, network_listener_factory)
    connection.start_listening()
    return connection

async def start_server(address: NetworkAddress, network_listener_factory = lambda address: NetworkListener(address)) -> Server:
    server = Server(address, network_listener_factory)
    await server.start()
    return server