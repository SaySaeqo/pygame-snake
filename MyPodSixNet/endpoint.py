import asyncio
from helpers import NetworkAddress
from icecream import ic
from json import dumps, loads

def pop_till_empty(queue: asyncio.Queue):
    while not queue.empty():
        yield queue.get_nowait()

END_SEQ = b"\0---\0"

class EndPoint:

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, network_listener_factory):
        self.reader = reader
        self.writer = writer
        self.address = NetworkAddress(*writer.get_extra_info('peername')[:2])
        self.sendqueue: asyncio.Queue[dict] = asyncio.Queue()
        self.recqueue: asyncio.Queue[dict] = asyncio.Queue()
        self.receiver_task = None
        self.network_listener = network_listener_factory(self.address)

        self.send(action="connected")

    def __del__(self):
        self.stop_listening()
        self.writer.close()

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
            ic(self.address, connectionError)
            self.stop_listening()

    async def receiver(self):
        try:
            while True:
                data = await self.reader.readuntil(END_SEQ)
                data = data[:-len(END_SEQ)]  
                data = loads(data)
                await self.recqueue.put(data)
        except asyncio.CancelledError as cancelledError:
            self.send(action="disconnected")
            raise cancelledError

    def send(self, data = None, action: str = "default"):
        self.sendqueue.put_nowait({
            "action": action,
            "data": data
        })

    async def pump(self):
        # empty the sendqueue
        for data in pop_till_empty(self.sendqueue):
            self.writer.write(dumps(data).encode() + END_SEQ)
        await self.writer.drain()

        # empty the recqueue
        for data in pop_till_empty(self.recqueue):
            [getattr(self.network_listener, n)(data["data"]) for n in ("Network_" + data["action"], "Network") if hasattr(self.network_listener, n)]