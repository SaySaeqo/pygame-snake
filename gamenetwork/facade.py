import asyncio
import json
import logging
import toolz
import typing
import socket

LOG = logging.getLogger(__package__)
END_SEQ = b"\0---\0"
START_SEQ = b"\0+++\0"
_Address = tuple[str, int]

tcp_connections: dict[_Address, tuple[asyncio.Transport, asyncio.Protocol]] = {} # There are multiple connections for server only
udp_connection: tuple[asyncio.DatagramTransport, asyncio.DatagramProtocol] = None
server: asyncio.Server = None

class NetworkListener:
    def __init__(self, address: tuple[str, int]) -> None:
        self.address = address

    def action_someexample(self, data):
        LOG.debug("Action 'someexample' from " + str(self.address))

    def interceptor(self, action, data):
        LOG.debug(f"Action {action} from " + str(self.address))

    def connected(self):
        LOG.debug("Connected to " + str(self.address))

    def disconnected(self):
        LOG.debug("Disconnected from " + str(self.address))


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
            action = d["action"]
            data = d["data"]
            listener.interceptor(action, data)
            handler_name = "action_" + action
            if hasattr(listener, handler_name):
                getattr(listener, handler_name)(data)
    except Exception as e:
        LOG.error(f"Error while processing data: {original_data}")
        raise e
    

class _GeneralProtocol(asyncio.Protocol):
    
    def __init__(self, network_listener_factory: typing.Callable[[tuple[str, int]], NetworkListener]):
        self.network_listener_factory = network_listener_factory
        self.network_listener = None

    def connection_made(self, transport: asyncio.BaseTransport):
        # retrieve the peer address
        self.transport_address = transport.get_extra_info('peername')[:2]
        
        # create network listener
        self.network_listener = self.network_listener_factory(self.transport_address)
        self.network_listener.connected()

        # store connection in global variable
        global tcp_connections
        tcp_connections[self.transport_address] = (transport, self)

        # set network listener for UDP connection
        global udp_connection
        udp_connection[1].network_listener = self.network_listener

    def data_received(self, data):
        _distribute_data(data, self.network_listener)

    def connection_lost(self, exc):
        if exc:
            raise Exception("TCP connection lost due to error: {}".format(exc))
        self.network_listener.disconnected()
        global tcp_connections
        try:
            if not tcp_connections[self.transport_address][0].is_closing():
                LOG.warning(f"Connection lost but not closed: {self.transport_address}")
                tcp_connections[self.transport_address][0].close()
            del tcp_connections[self.transport_address]
        except KeyError:
            pass

class _GeneralDatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.network_listener = None

    def datagram_received(self, data, addr):
        _distribute_data(data, self.network_listener)

    def error_received(self, exc):
        LOG.warning("UDB error: {}".format(exc))

    def connection_lost(self, exc):
        if exc:
            raise Exception("UDP connection lost due to error: {}".format(exc))

async def connect_to_server(address: tuple[str, int], network_listener_factory = lambda address: NetworkListener(address)):
    loop = asyncio.get_running_loop()
    global udp_connection
    udp_connection = await loop.create_datagram_endpoint(_GeneralDatagramProtocol, remote_addr=address)
    local_addr = udp_connection[0].get_extra_info("sockname")[:2]
    t, p = await loop.create_connection(lambda : _GeneralProtocol(network_listener_factory), *address, local_addr=local_addr)

async def start_server(address: tuple[str, int], network_listener_factory = lambda address: NetworkListener(address)):
    loop = asyncio.get_running_loop()
    global udp_connection, server
    udp_connection = await loop.create_datagram_endpoint(_GeneralDatagramProtocol, local_addr=address)
    server = await loop.create_server(lambda : _GeneralProtocol(network_listener_factory), *address)

def send(action: str, data = None, to: tuple[str, int] = None):
    LOG.debug(f"Sending TCP action '{action}' to {to}")
    if to:
        try:
            tcp_connections[to][0].write(_get_sendready_data(action, data))
        except KeyError:
            LOG.warning(f"Could not send message to {to}. No such connection.")
    else:
        for transport, _ in tcp_connections.values():
            transport.write(_get_sendready_data(action, data))
        

def send_udp(action: str, data = None, to: tuple[str, int] = None):
    if not udp_connection:
        return
    LOG.debug(f"Sending UDP action '{action}' to {to}")
    if to:
        udp_connection[0].sendto(_get_sendready_data(action, data), to)
    else:
        for address in tcp_connections:
            udp_connection[0].sendto(_get_sendready_data(action, data), address)
        

def is_connected(address: tuple[str, int]) -> bool:
    try:
        address = socket.gethostbyname(address[0]), address[1]
        return not tcp_connections[address][0].is_closing()
    except KeyError:
        return False

def close():
    """ Resets global variables and closes all connections. """
    LOG.debug("Closing connections")
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
    
class ContextManager:
    def __enter__(self): pass
    def __exit__(self, exc_type, exc_value, traceback): close()