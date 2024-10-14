import asyncio
from address import *
from json import dumps, loads
from logger import *

class EndPoint:
    
    END_SEQ = b"\0---\0"

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, network_listener_factory):
        self.reader = reader
        self.writer = writer
        self.address = NetworkAddress(*writer.get_extra_info('peername')[:2])
        self.sendqueue: asyncio.Queue[dict] = asyncio.Queue()
        self.recqueue: asyncio.Queue[dict] = asyncio.Queue()
        self.receiver_task = None
        self.network_listener = network_listener_factory(self)

    def __del__(self):
        self.stop_listening()
        try:
            self.writer.close()
        except RuntimeError as runtimeError:
            pass


    def stop_listening(self):
        if self.receiver_task:
            self.receiver_task.cancel()

    def __await__(self):
        if self.receiver_task:
            return self.receiver_task.__await__()
        else:
            raise RuntimeError("Endpoint not started yet.")

    def start_listening(self):
        try:
            self.receiver_task = asyncio.create_task(self.receiver())
        except ConnectionError as connectionError:
            LOG.warning("Connection error from %s: %s", self.address, connectionError)
            self.stop_listening()

    async def receiver(self):
        await self.send_now(action="connected")
        try:
            while True:
                data = await self.reader.readuntil(self.END_SEQ)
                data = data[:-len(self.END_SEQ)]  
                data = loads(data)
                await self.recqueue.put(data)
        except asyncio.CancelledError as cancelledError:
            await self.send_now(action="disconnected")
            raise cancelledError

    def send(self, data = None, action: str = "default"):
        self.sendqueue.put_nowait({
            "action": action,
            "data": data
        })

    async def send_now(self, data = None, action: str = "default"):
        self.writer.write(dumps({
            "action": action,
            "data": data
        }).encode() + self.END_SEQ)
        await self.writer.drain()

    async def pump(self):
        # empty the sendqueue
        while not self.sendqueue.empty():
            data = self.sendqueue.get_nowait()
            self.writer.write(dumps(data).encode() + self.END_SEQ)
        await self.writer.drain()

        # empty the recqueue
        while not self.recqueue.empty():
            data = self.recqueue.get_nowait()
            handler_name = "Network_" + data["action"]
            if hasattr(self.network_listener, handler_name):
                getattr(self.network_listener, handler_name)(data["data"])
            self.network_listener.Network(data)