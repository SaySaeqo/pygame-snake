import asyncio
import atexit
import json
import logging
import toolz

LOG = logging.getLogger(__package__)
END_SEQ = b"\0---\0"
START_SEQ = b"\0+++\0"

connections = {}
server = None

class NetworkListener:
    def __init__(self, address: tuple[str, int]) -> None:
        self.address = address

    def action_someexample(self, data):
        LOG.debug("Action 'someexample' from " + str(self.address))

    def interceptor(self, data):
        LOG.debug(f"Action {data['action']} from " + str(self.address))

    def connected(self):
        LOG.debug("Connected to " + str(self.address))

    def disconnected(self):
        LOG.debug("Disconnected from " + str(self.address))

def get_chunked_data(bytestream: bytes):
    while True:
        start = bytestream.find(START_SEQ)
        end = bytestream.find(END_SEQ)
        if end < start:
            bytestream = bytestream[start:]
            start = 0
            end = bytestream.find(END_SEQ)
        if start == -1 or end == -1:
            return
        yield bytestream[start + len(START_SEQ):end]
        bytestream = bytestream[end + len(END_SEQ):]
    

class GeneralProtocol(asyncio.Protocol):
    
    def __init__(self, network_listener_factory):
        self.network_listener_factory = network_listener_factory

    def connection_made(self, transport: asyncio.Transport):
        ip, port = transport.get_extra_info('peername')[:2]
        if not all(map(lambda x: x.isdigit() , ip.split("."))):
            ip = "localhost"
        self.transport_address = ip, port
        self.network_listener: NetworkListener = self.network_listener_factory(self.transport_address)
        self.network_listener.connected()
        global connections
        connections[self.transport_address] = (transport, self)

    def data_received(self, data):
        original_data = data
        try:
            data = get_chunked_data(data)
            data = map(lambda x: json.loads(x.decode()), data)
            data = toolz.unique(data, lambda x: x["action"])
            for d in data:
                self.network_listener.interceptor(d)
                handler_name = "action_" + d["action"]
                if hasattr(self.network_listener, handler_name):
                    getattr(self.network_listener, handler_name)(d["data"])
        except Exception as e:
            LOG.error(f"Error while processing data: {original_data}")
            raise e

    def connection_lost(self, exc):
        if exc:
            LOG.error("Connection lost due to error: {}".format(exc))
        self.network_listener.disconnected()
        global connections
        try:
            if not connections[self.transport_address][0].is_closing():
                LOG.error(f"Connection lost but not closed: {self.transport_address}")
                connections[self.transport_address][0].close()
            del connections[self.transport_address]
        except KeyError:
            pass


async def connect_to_server(address: tuple[str, int], network_listener_factory = lambda address: NetworkListener(address)):
    loop = asyncio.get_running_loop()
    t, p = await loop.create_connection(lambda : GeneralProtocol(network_listener_factory), address[0], address[1])

async def start_server(address: tuple[str, int], network_listener_factory = lambda address: NetworkListener(address)):
    loop = asyncio.get_running_loop()
    global server
    if server:
        raise Exception("Only one server can be started at a time.")
    server = await loop.create_server(lambda : GeneralProtocol(network_listener_factory), address[0], address[1])

def send(action: str, data = None, to: tuple[str, int] = None):
    if to is None:
        for transport, _ in connections.values():
            send_with_transport(transport, action, data)
    else:
        try:
            send_with_transport(connections[to][0], action, data)
        except KeyError:
            LOG.error(f"Could not send message to {to}. No such connection.")

def send_with_transport(transport: asyncio.WriteTransport, action: str, data = None):
    transport.write(START_SEQ + json.dumps({
        "action": action,
        "data": data
    }).encode() + END_SEQ)

def is_connected(address: tuple[str, int]):
    try:
        return not connections[address][0].is_closing()
    except KeyError:
        return False

@atexit.register
def close():
    global server
    if server:
        server.close()
    server = None
    global connections
    for transport, _ in connections.values():
        transport.write_eof()
    connections.clear()