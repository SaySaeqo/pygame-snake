import asyncio
import atexit
import json
import logging
import toolz
import typing

LOG = logging.getLogger(__package__)
END_SEQ = b"\0---\0"
START_SEQ = b"\0+++\0"

connections = {}
connection_udp = None
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

def get_sendready_data(action: str, data = None) -> bytes:
    return START_SEQ + json.dumps({
        "action": action,
        "data": data
    }).encode() + END_SEQ

def get_readready_data_generator(bytestream: bytes) -> typing.Generator[typing.Any, None, None]:
    search_start = 0
    def segment():
        nonlocal search_start
        return bytestream[search_start:]
    while True:
        start = segment().find(START_SEQ)
        end = segment().find(END_SEQ)
        if end < start:
            search_start += start
            start = 0
            end = segment().find(END_SEQ)
        if start == -1 or end == -1:
            return
        yield json.loads(segment()[start + len(START_SEQ):end].decode())
        search_start += end + len(END_SEQ)
    
def distribute_data(data: bytes, listener: NetworkListener):
    original_data = data
    try:
        data = get_readready_data_generator(data)
        data = toolz.unique(data, lambda x: x["action"])
        for d in data:
            listener.interceptor(d)
            handler_name = "action_" + d["action"]
            if hasattr(listener, handler_name):
                getattr(listener, handler_name)(d["data"])
    except Exception as e:
        LOG.error(f"Error while processing data: {original_data}")
        raise e

class GeneralProtocol(asyncio.BaseProtocol):
    
    def __init__(self, network_listener_factory):
        self.network_listener_factory = network_listener_factory
        self.network_listener = None

    def connection_made(self, transport: asyncio.BaseTransport):
        if isinstance(transport, asyncio.DatagramTransport):
            LOG.info(f"Connected made via UDP.")
            global connection_udp
            connection_udp = (transport, self)
            return
        address = transport.get_extra_info('peername')
        ip, port = address[:2]
        if not all(map(lambda x: x.isdigit() , ip.split("."))):
            ip = "localhost"
        self.transport_address = ip, port
        self.network_listener: NetworkListener = self.network_listener_factory(self.transport_address)
        self.network_listener.connected()
        global connections
        connections[self.transport_address] = (transport, self, None)
        transport.write(get_sendready_data("udb_connected", connection_udp[0].get_extra_info('sockname')[1]))

    def data_received(self, data):
        d = get_readready_data_generator(data)
        for dd in d:
            if dd["action"] == "udb_connected":
                port = dd["data"]
                global connections
                connections[self.transport_address] = (connections[self.transport_address][0], connections[self.transport_address][1], (self.transport_address[0], port))
                global connection_udp
                transport_address = (self.transport_address[0], port)
                connection_udp[1].transport_address = transport_address
                connection_udp[1].network_listener = connection_udp[1].network_listener_factory(transport_address)
                # TODO zrobić coś z podwójnym wywołaniem connected i disconnected
                connection_udp[1].network_listener.connected()
        distribute_data(data, self.network_listener)
        
    def datagram_received(self, data, addr):
        distribute_data(data, self.network_listener)

    def error_received(self, exc):
        LOG.error("Error received: {}".format(exc))

    def eof_received(self):
        # TODO to faktycznie się wywołuje, do ogarnięcia czy można bez tego
        LOG.info("EOF received")

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
    udp_address = address[0], address[1] + 1
    u_t, u_p = await loop.create_datagram_endpoint(lambda : GeneralProtocol(network_listener_factory), remote_addr=udp_address)
    t, p = await loop.create_connection(lambda : GeneralProtocol(network_listener_factory), address[0], address[1])

async def start_server(address: tuple[str, int], network_listener_factory = lambda address: NetworkListener(address)):
    loop = asyncio.get_running_loop()
    global server
    if server:
        raise Exception("Only one server can be started at a time.")
    server = await loop.create_server(lambda : GeneralProtocol(network_listener_factory), address[0], address[1])
    udp_address = address[0], address[1] + 1
    await loop.create_datagram_endpoint(lambda : GeneralProtocol(network_listener_factory), local_addr=udp_address)

def send(action: str, data = None, to: tuple[str, int] = None):
    if to is None:
        for transport, _, _ in connections.values():
            transport.write(get_sendready_data(action, data))
    else:
        try:
            connections[to][0].write(get_sendready_data(action, data))
        except KeyError:
            LOG.error(f"Could not send message to {to}. No such connection.")

def send_udp(action: str, data = None, to: tuple[str, int] = None):
    # TODO implement error handling and None handling especially
    if to is None:
        for _, _, udp_address in connections.values():
            connection_udp[0].sendto(get_sendready_data(action, data), udp_address)
    else:
        try:
            udp_address = connections[to][2]
            connection_udp[0].sendto(get_sendready_data(action, data), udp_address)
        except KeyError:
            LOG.error(f"Could not send UDP message to {to}. No such connection.")

def is_connected(address: tuple[str, int]) -> bool:
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
    for transport, _, _ in connections.values():
        transport.write_eof()
    connections.clear()
    global connection_udp
    if connection_udp:
        transport, _ = connection_udp
        transport.close()
        connection_udp = None