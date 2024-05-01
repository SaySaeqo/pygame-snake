import asyncio
from MyPodSixNet import NetworkAddress
from icecream import ic
from endpoint import EndPoint


class Server:

    def __init__(self, address: NetworkAddress, network_listener_factory):
        self.address: NetworkAddress = address
        self.connections = {}
        self.serving_task = None
        self.network_listener_factory = network_listener_factory

    def __del__(self):
        for conn in self.connections.values():
            del conn
        self.serving_task.cancel()

    async def __await__(self):
        if self.serving_task:
            await self.serving_task
        else:
            ic("Server not started yet.")
        while self.connections:
            await asyncio.sleep(0)


    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        connection = EndPoint(reader, writer, network_listener_factory=self.network_listener_factory)

        connection.start_listening()
        self.connections[connection.address] = connection

        await connection
        writer.close()

        del self.connections[connection.address]
        
        

    async def start(self):
        server = await asyncio.start_server(self.handle_client, self.address.ip, self.address.port)

        self.serving_task = asyncio.create_task(server.serve_forever())

    def send(self, data, to: NetworkAddress = None, action = "default"):
        if to is None:
            [conn.send(data, action) for conn in self.connections.values()]
        else:
            self.connections[to].send(data, action)

    async def pump(self):
        [await conn.pump() for conn in self.connections.values()]