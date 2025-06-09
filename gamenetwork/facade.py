import asyncio
import json
import logging
import toolz
import typing
import socket
from dataclasses import dataclass

LOG = logging.getLogger(__package__)
END_SEQ = b"\0---\0"
START_SEQ = b"\0+++\0"
HOLE_PUNCHING_ACTION = "holepunching"
NEW_UDP_PORT_ACTION = "newudpport"
HOLE_PUNCHING_INTERVAL = 1.0
_Address = tuple[str, int]
@dataclass
class Connection:
    transport: asyncio.Transport
    protocol: asyncio.Protocol
    udp_port: int
@dataclass
class UDPConnection:
    transport: asyncio.DatagramTransport
    protocol: asyncio.DatagramProtocol

tcp_connections: dict[_Address, Connection] = {} # There are multiple connections for server only
def get_tcp_connection_by_udp_port(ip: str, udp_port: int) -> Connection:
    correct_ip = filter(lambda x: x[0] == ip, tcp_connections)
    correct_address = list(filter(lambda x: tcp_connections[x].udp_port == udp_port, correct_ip))
    if len(correct_address) > 1:
        return tcp_connections[correct_address[0]]
    return None
def update_udb_port(ip, old_port, new_port: int):
    connection = get_tcp_connection_by_udp_port(ip, old_port)
    if connection:
        connection.udp_port = new_port
def remove_tcp_connection(address: _Address):
    global tcp_connections
    try:
        if not tcp_connections[address].transport.is_closing():
            LOG.warning(f"Connection lost but not closed: {address}")
            tcp_connections[address].transport.close()
        del tcp_connections[address]
        LOG.debug(f"Connection lost with {address}")
    except KeyError:
        pass

udp_connection: UDPConnection = None
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

class ActionError(Exception): ...
def _find_action_data(data: bytes, action: str) -> typing.Any:
    for d in _get_readready_data_generator(data):
        if d["action"] == action:
            return d["data"]
    raise ActionError(f"Action '{action}' not found")
    

class _GeneralProtocol(asyncio.Protocol):
    
    def __init__(self, network_listener_factory: typing.Callable[[tuple[str, int]], NetworkListener], udp_port: int):
        self.network_listener_factory = network_listener_factory
        self.network_listener = None
        self.udp_port_at_start = udp_port

    def connection_made(self, transport: asyncio.Transport):
        # retrieve the peer address
        self.transport_address = transport.get_extra_info('peername')[:2]
        
        # create network listener
        self.network_listener = self.network_listener_factory(self.transport_address)
        self.network_listener.connected()

        # store connection in global variable
        global tcp_connections
        udp_port = self.udp_port_at_start if self.udp_port_at_start else self.transport_address[1]
        tcp_connections[self.transport_address] = Connection(transport, self, udp_port)
        LOG.debug(f"Connection made with {self.transport_address}")

        # set network listener for UDP connection
        global udp_connection
        udp_connection.protocol.network_listener = self.network_listener

    def data_received(self, data):
        try:
            new_udp_port = _find_action_data(data, NEW_UDP_PORT_ACTION)
            global udp_connection
            udp_connection.protocol.public_udp_port = new_udp_port
            LOG.info(f"New public UDP port: {new_udp_port}")
        except ActionError: ...
        _distribute_data(data, self.network_listener)

    def connection_lost(self, exc):
        if exc:
            raise Exception("TCP connection lost due to error: {}".format(exc))
        self.network_listener.disconnected()
        remove_tcp_connection(self.transport_address)
        

class _GeneralDatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.network_listener = None

    def connection_made(self, transport: asyncio.DatagramTransport):
        self.public_udp_port = transport.get_extra_info("sockname")[1]
        async def holepunching(protocol):
            while not transport.is_closing():
                send_udp(HOLE_PUNCHING_ACTION, protocol.public_udp_port)
                await asyncio.sleep(HOLE_PUNCHING_INTERVAL)
        asyncio.create_task(holepunching(self))

    def datagram_received(self, data, addr):
        try:
            previous_udp_port = _find_action_data(data, HOLE_PUNCHING_ACTION)
            if previous_udp_port != addr[1]:
                update_udb_port(addr[0], previous_udp_port, addr[1])
                send(NEW_UDP_PORT_ACTION, addr[1], get_tcp_connection_by_udp_port(*addr).protocol.transport_address)
        except ActionError: ...
        _distribute_data(data, self.network_listener)

    def error_received(self, exc):
        LOG.warning("UDB error: {}".format(exc))

    def connection_lost(self, exc):
        if exc:
            raise Exception("UDP connection lost due to error: {}".format(exc))

async def connect_to_server(address: tuple[str, int], network_listener_factory = lambda address: NetworkListener(address), udp_port=None):
    loop = asyncio.get_running_loop()
    global udp_connection
    t, p = await loop.create_datagram_endpoint(_GeneralDatagramProtocol, local_addr=("0.0.0.0", 0))
    udp_connection = UDPConnection(t, p)
    local_addr = t.get_extra_info("sockname")[:2]
    t, p = await loop.create_connection(lambda : _GeneralProtocol(network_listener_factory, udp_port), *address, local_addr=local_addr)
    LOG.debug(f"Connection listen on address {local_addr}")

async def start_server(address: tuple[str, int], network_listener_factory = lambda address: NetworkListener(address)):
    loop = asyncio.get_running_loop()
    global udp_connection, server
    t, p = await loop.create_datagram_endpoint(_GeneralDatagramProtocol, local_addr=address)
    udp_connection = UDPConnection(t, p)
    server = await loop.create_server(lambda : _GeneralProtocol(network_listener_factory), *address)

def send(action: str, data = None, to: tuple[str, int] = None):
    LOG.debug(f"Sending TCP action '{action}' to {to}")
    if to:
        try:
            tcp_connections[to].transport.write(_get_sendready_data(action, data))
        except KeyError:
            LOG.warning(f"Could not send message to {to}. No such connection.")
    else:
        for connection in tcp_connections.values():
            connection.transport.write(_get_sendready_data(action, data))
        

def send_udp(action: str, data = None, to: tuple[str, int] = None):
    if not udp_connection:
        return
    if to:
        connection = tcp_connections[to]
        corrected_to = to[0], connection.udp_port
        udp_connection.transport.sendto(_get_sendready_data(action, data), corrected_to)
    else:
        for address, connection in tcp_connections.items():
            corrected_address = address[0], connection.udp_port
            udp_connection.transport.sendto(_get_sendready_data(action, data), corrected_address)
        

def is_connected(address: tuple[str, int]) -> bool:
    try:
        address = socket.gethostbyname(address[0]), address[1]
        return not tcp_connections[address].transport.is_closing()
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
    for connection in tcp_connections.values():
        connection.transport.write_eof()
    tcp_connections.clear()

    global udp_connection
    if udp_connection:
        udp_connection.transport.close()
    udp_connection = None
    
class ContextManager:
    def __enter__(self): pass
    def __exit__(self, exc_type, exc_value, traceback): close()