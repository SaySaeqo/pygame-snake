import asyncio
import atexit
import json
import logging
import toolz
import typing

LOG = logging.getLogger(__package__)
END_SEQ = b"\0---\0"
START_SEQ = b"\0+++\0"
UDP_HANDSHAKE_ACTION_NAME = "udp_connected"

connections = {}
udp_addresses = {}
connection_udp: tuple[asyncio.DatagramTransport, asyncio.DatagramProtocol] = None
server: asyncio.Server = None

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

    def udp_connected(self):
        LOG.debug("UDP connected to " + str(self.address))

    def udp_disconnected(self):
        LOG.debug("UDP disconnected from " + str(self.address))

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

class GeneralProtocol(asyncio.Protocol):
    
    def __init__(self, network_listener_factory):
        self.network_listener_factory = network_listener_factory
        self.network_listener = None

    def connection_made(self, transport: asyncio.BaseTransport):
        address = transport.get_extra_info('peername')
        ip, port = address[:2]
        if not all(map(lambda x: x.isdigit() , ip.split("."))):
            ip = "localhost"
        self.transport_address = ip, port
        self.network_listener: NetworkListener = self.network_listener_factory(self.transport_address)
        self.network_listener.connected()
        global connections
        connections[self.transport_address] = (transport, self)
        transport.write(get_sendready_data(UDP_HANDSHAKE_ACTION_NAME, connection_udp[0].get_extra_info('sockname')[1]))

    def data_received(self, data):
        global udp_addresses
        if not self.transport_address in udp_addresses.keys():
            port = next((_["data"] for _ in get_readready_data_generator(data) if _["action"] == UDP_HANDSHAKE_ACTION_NAME), None)
            if port:
                udp_address = self.transport_address[0], port
                udp_addresses[self.transport_address] = udp_address
                global connection_udp
                # TODO connection_udp is None while reconnecting ??
                connection_udp[1].network_listener = self.network_listener
        distribute_data(data, self.network_listener)

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
                LOG.warning(f"Connection lost but not closed: {self.transport_address}")
                connections[self.transport_address][0].close()
            del connections[self.transport_address]
        except KeyError:
            pass

class GeneralDatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.network_listener: NetworkListener = None

    def connection_made(self, transport: asyncio.DatagramProtocol):
        global connection_udp
        connection_udp = (transport, self)
        
    def datagram_received(self, data, addr):
        distribute_data(data, self.network_listener)

    def error_received(self, exc):
        LOG.error("Error received: {}".format(exc))

    def connection_lost(self, exc):
        if exc:
            LOG.error("UDP connection lost due to error: {}".format(exc))

        if self.network_listener:
            self.network_listener.udp_disconnected()
    
        global connection_udp
        if connection_udp and not connection_udp[0].is_closing():
            LOG.warning(f"UDP connection lost but not closed.")
            connection_udp[0].close()
        connection_udp = None

        global udp_addresses
        udp_addresses.clear()


async def connect_to_server(address: tuple[str, int], network_listener_factory = lambda address: NetworkListener(address)):
    loop = asyncio.get_running_loop()
    udp_address = address[0], address[1] + 1
    u_t, u_p = await loop.create_datagram_endpoint(GeneralDatagramProtocol, remote_addr=udp_address)
    t, p = await loop.create_connection(lambda : GeneralProtocol(network_listener_factory), address[0], address[1])

async def start_server(address: tuple[str, int], network_listener_factory = lambda address: NetworkListener(address)):
    loop = asyncio.get_running_loop()
    global server
    if server:
        raise Exception("Only one server can be started at a time.")
    server = await loop.create_server(lambda : GeneralProtocol(network_listener_factory), address[0], address[1])
    udp_address = address[0], address[1] + 1
    await loop.create_datagram_endpoint(GeneralDatagramProtocol, local_addr=udp_address)

def send(action: str, data = None, to: tuple[str, int] = None):
    if to is None:
        for transport, _ in connections.values():
            transport.write(get_sendready_data(action, data))
    else:
        try:
            connections[to][0].write(get_sendready_data(action, data))
        except KeyError:
            LOG.error(f"Could not send message to {to}. No such connection.")

def send_udp(action: str, data = None, to: tuple[str, int] = None):
    # TODO implement error handling and None handling especially
    if to is None:
        for udp_address in udp_addresses.values():
            connection_udp[0].sendto(get_sendready_data(action, data), udp_address)
    else:
        try:
            udp_address = udp_addresses[to]
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
    for transport, _ in connections.values():
        transport.write_eof()
    connections.clear()

    global connection_udp
    if connection_udp:
        transport, _ = connection_udp
        transport.close()
    connection_udp = None

    global udp_addresses
    udp_addresses.clear()