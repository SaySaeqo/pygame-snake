import asyncio
import atexit
import json
import logging
import toolz
import typing
import socket

LOG = logging.getLogger(__package__)
END_SEQ = b"\0---\0"
START_SEQ = b"\0+++\0"
UDP_HANDSHAKE_ACTION_NAME = "udp_handshake"
_Address = tuple[str, int]

tcp_connections: dict[_Address, tuple[asyncio.Transport, asyncio.Protocol]] = {} # There are multiple connections for server only
tcp2udp_addresses_map: dict[_Address, _Address] = {}
udp_connection: tuple[asyncio.DatagramTransport, asyncio.DatagramProtocol] = None
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
        """ Called after UDP handshake is accepted. """
        LOG.info("UDP handshake accepted from " + str(self.address))

    def udp_disconnected(self):
        LOG.debug("UDP disconnected from " + str(self.address))

class MultipleEndpointsError(Exception):
    pass

class ActionError(Exception):
    pass

def _get_sendready_data(action: str, data = None) -> bytes:
    return START_SEQ + json.dumps({
        "action": action,
        "data": data
    }).encode() + END_SEQ

def _get_readready_data_generator(bytestream: bytes) -> typing.Generator[typing.Any, None, None]:
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
    
def _distribute_data(data: bytes, listener: NetworkListener):
    original_data = data
    try:
        data = _get_readready_data_generator(data)
        data = toolz.unique(data, lambda x: x["action"])
        for d in data:
            listener.interceptor(d)
            handler_name = "action_" + d["action"]
            if hasattr(listener, handler_name):
                getattr(listener, handler_name)(d["data"])
    except Exception as e:
        LOG.error(f"Error while processing data: {original_data}")
        raise e
    
def _find_action_data(data: bytes, action: str) -> typing.Any:
    for d in _get_readready_data_generator(data):
        if d["action"] == action:
            return d["data"]
    raise ActionError(f"Action '{action}' not found")
    

class GeneralProtocol(asyncio.Protocol):
    
    def __init__(self, network_listener_factory):
        self.network_listener_factory = network_listener_factory
        self.network_listener = None

    def connection_made(self, transport: asyncio.BaseTransport):
        # retrieve the peer address
        ip, port = transport.get_extra_info('peername')[:2]
        if not all(map(lambda x: x.isdigit() , ip.split("."))):
            ip = "localhost"
        self.transport_address = ip, port
        
        # create network listener
        self.network_listener: NetworkListener = self.network_listener_factory(self.transport_address)
        self.network_listener.connected()

        # store connection in global variable
        global tcp_connections
        tcp_connections[self.transport_address] = (transport, self)

        # send UDP handshake
        transport.write(_get_sendready_data(UDP_HANDSHAKE_ACTION_NAME, udp_connection[0].get_extra_info('sockname')[1]))

    def data_received(self, data):

        # await UDB handshake
        global tcp2udp_addresses_map
        global udp_connection
        if udp_connection and not self.transport_address in tcp2udp_addresses_map:
            try:
                port = _find_action_data(data, UDP_HANDSHAKE_ACTION_NAME)
                udp_address = self.transport_address[0], port
                tcp2udp_addresses_map[self.transport_address] = udp_address
                udp_connection[1].network_listener = self.network_listener
                self.network_listener.udp_connected()
            except ActionError as e:
                pass

        _distribute_data(data, self.network_listener)

    def connection_lost(self, exc):
        if exc:
            LOG.error("Connection lost due to error: {}".format(exc))
        self.network_listener.disconnected()
        global tcp_connections
        try:
            if not tcp_connections[self.transport_address][0].is_closing():
                LOG.warning(f"Connection lost but not closed: {self.transport_address}")
                tcp_connections[self.transport_address][0].close()
            del tcp_connections[self.transport_address]
        except KeyError:
            pass

class GeneralDatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.network_listener: NetworkListener = None
        
    def datagram_received(self, data, addr):
        _distribute_data(data, self.network_listener)

    def error_received(self, exc):
        LOG.warning("Error received: {}".format(exc))

    def connection_lost(self, exc):
        if exc:
            LOG.error("UDP connection lost due to error: {}".format(exc))

        if self.network_listener:
            self.network_listener.udp_disconnected()
    
        global udp_connection
        if udp_connection and not udp_connection[0].is_closing():
            LOG.warning(f"UDP connection lost but not closed.")
            udp_connection[0].close()
        udp_connection = None

        global tcp2udp_addresses_map
        tcp2udp_addresses_map.clear()


async def connect_to_server(address: tuple[str, int], network_listener_factory = lambda address: NetworkListener(address)):
    loop = asyncio.get_running_loop()
    global udp_connection
    if udp_connection:
        raise MultipleEndpointsError("Only one UDP connection can be started at a time (client).")
    udp_connection = await loop.create_datagram_endpoint(lambda: GeneralDatagramProtocol(), remote_addr=address)
    t, p = await loop.create_connection(lambda : GeneralProtocol(network_listener_factory), address[0], address[1])

async def start_server(address: tuple[str, int], network_listener_factory = lambda address: NetworkListener(address)):
    loop = asyncio.get_running_loop()
    global udp_connection
    if udp_connection:
        raise MultipleEndpointsError("Only one UDP connection can be started at a time (server).")
    udp_connection = await loop.create_datagram_endpoint(lambda: GeneralDatagramProtocol(), local_addr=address)
    global server
    if server:
        raise MultipleEndpointsError("Only one server can be started at a time.")
    server = await loop.create_server(lambda : GeneralProtocol(network_listener_factory), address[0], address[1])

def send(action: str, data = None, to: tuple[str, int] = None):
    if to is None:
        for transport, _ in tcp_connections.values():
            transport.write(_get_sendready_data(action, data))
    else:
        try:
            tcp_connections[to][0].write(_get_sendready_data(action, data))
        except KeyError:
            LOG.error(f"Could not send message to {to}. No such connection.")

def send_udp(action: str, data = None, to: tuple[str, int] = None):
    if not udp_connection:
        return
    if to is None:
        for udp_address in tcp2udp_addresses_map.values():
            udp_connection[0].sendto(_get_sendready_data(action, data), udp_address)
    else:
        try:
            udp_address = tcp2udp_addresses_map[to]
            udp_connection[0].sendto(_get_sendready_data(action, data), udp_address)
        except KeyError:
            LOG.error(f"Could not send UDP message to {to}. No such connection.")

def is_connected(address: tuple[str, int]) -> bool:
    try:
        return not tcp_connections[address][0].is_closing()
    except KeyError:
        return False

@atexit.register
def close():
    """ Resets global variables and closes all connections. Automatically called at exit. """
    global server
    if server:
        server.close()
    server = None

    global tcp_connections
    for transport, _ in tcp_connections.values():
        transport.write_eof()
    tcp_connections.clear()

    global udp_connection
    if udp_connection:
        transport, _ = udp_connection
        transport.close()
    udp_connection = None

    global tcp2udp_addresses_map
    tcp2udp_addresses_map.clear()