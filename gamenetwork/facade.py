import asyncio
import json
import logging
import toolz
import typing
import randomname

LOG = logging.getLogger("gamenetwork")
END_SEQ = b"\0---\0"
START_SEQ = b"\0+++\0"

class Connection:
    def __init__(self, transport: asyncio.Transport, protocol: asyncio.Protocol, udp_port: int):
        self.transport = transport
        self.protocol = protocol
        self.udp_port = udp_port
    @property
    def udp_address(self):
        return (self.protocol.transport_address[0], self.udp_port) if self.udp_port else None
    def __del__(self):
        if not self.transport.is_closing():
            self.transport.close()
        
class UDPConnection:
    def __init__(self, transport: asyncio.DatagramTransport, protocol: asyncio.DatagramProtocol):
        self.transport = transport
        self.protocol = protocol
    def __del__(self):
        if not self.transport.is_closing():
            self.transport.close()

tcp_connections: dict[str, Connection] = {} # There are multiple connections for server only
udp_connection: UDPConnection = None
server: asyncio.Server = None
listener = None

def _get_sendready_data(action: str, data = None, _id = None) -> bytes:
    return START_SEQ + json.dumps({
        "action": action,
        "data": data,
        "_id": _id
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
    
def _distribute_data(data: bytes, addr, transport=None, protocol=None):
    original_data = data
    try:
        data = _get_readready_data_generator(data)
        data = toolz.unique(data, lambda x: x["action"])
    except Exception as e: # I don't know what can go wrong here so I will leave that 'except' and wait...
        LOG.error(f"Error while processing data: {original_data}")
        raise e
    for d in data:
        action: str = d["action"]
        data = d["data"]
        _id = d["_id"]
        listener.__prepare(_id, addr, transport, protocol)
        listener.interceptor(action, data)
        # execute actions for fully connected connections or internal actions
        if tcp_connections.get(_id) or action.startswith("_"):
            try:
                getattr(listener, "action_" + action)(data)
            except AttributeError:
                LOG.warning(f"Action '{action}' from {_id} is not registered in network listener!")

class _GeneralProtocol(asyncio.Protocol):
    
    def __init__(self):
        self._id = None

    def connection_made(self, transport: asyncio.Transport):
        self.transport_address = transport.get_extra_info('peername')[:2]
        self.transport = transport
        LOG.debug(f"Connection made with {self.transport_address}")

    def data_received(self, data):
        _distribute_data(data, self.transport_address, self.transport, self)

    def connection_lost(self, exc):
        tcp_connections.pop(self._id, None) # delete from connections
        listener.__prepare(self._id, self.transport_address, self.transport, self)
        listener.disconnected()
        if exc:
            LOG.error(f"Connection lost due to error '{exc}' with {self._id}@{self.transport_address}")
        else:
            LOG.debug(f"Connection lost with {self._id}@{self.transport_address}")
        

class _GeneralDatagramProtocol(asyncio.DatagramProtocol):

    def connection_made(self, transport: asyncio.DatagramTransport):
        async def holepunching():
            while not transport.is_closing():
                send_udp("_hole_punching")
                await asyncio.sleep(1)
        asyncio.create_task(holepunching())
        LOG.debug("Hole punching task have been started.")

    def datagram_received(self, data, addr):
        _distribute_data(data, addr)
        # UDP port correction based on _id (was set in _distrubute_data)
        connection = tcp_connections.get(listener._id)
        if connection:
            connection.udp_port = addr[1]

    def error_received(self, exc):
        LOG.warning("UDB error: {}".format(exc))

    def connection_lost(self, exc):
        if exc:
            LOG.error(f"UDP connection lost due to error: {exc}")
        else:
            LOG.debug("UDP endpoint lost without error.")


def tcp_only(func):
    def wrapper(self, *args, **kwargs):
        try: 
            if self.transport == None or self.protocol == None:
                LOG.warning("You should not call internal method using UDP call!")
            else:
                func(self, *args, **kwargs)
        except AttributeError:
            LOG.error("You should not call internal method using UDP call!")
    return wrapper

class NetworkListener:
    def __prepare(self, _id: str, _address: str, transport: asyncio.Transport, protocol: _GeneralProtocol):
        self._id: str = _id
        self._address: str = _address
        self.transport = transport
        self.protocol = protocol
    def interceptor(self, action, data): ...
    def connected(self): ...
    def disconnected(self): ...

    # internal actions
    def action__hole_punching(self, data): ...

    ## client only
    @tcp_only
    def action__send_id_proposition(self, data):
        self.transport.write(_get_sendready_data("_check_if_id_is_available", _id = randomname.generate()))
    @tcp_only
    def action__confirm_id(self, data):
        tcp_connections[self._id] = Connection(self.transport, self.protocol, None)
        self.protocol._id = self._id
        self.connected()

    ## server only
    @tcp_only
    def action__check_if_id_is_available(self, data):
        if tcp_connections.get(self._id): # not available
            self.transport.write(_get_sendready_data("_send_id_proposition"))
        else: # available
            tcp_connections[self._id] = Connection(self.transport, self.protocol, None)
            self.protocol._id = self._id
            self.transport.write(_get_sendready_data("_confirm_id", _id = self._id))
            self.connected()


async def connect_to_server(ip: str, tcp_port: int, udp_port: int, network_listener: NetworkListener):
    # Assign global variables listed below
    global listener, udp_connection
    listener = network_listener
    loop = asyncio.get_running_loop()
    t, p = await loop.create_datagram_endpoint(_GeneralDatagramProtocol, local_addr=("0.0.0.0", 0), remote_addr=(ip, udp_port))
    udp_connection = UDPConnection(t, p)
    # Connect to server
    local_addr = t.get_extra_info("sockname")[:2]
    t, p = await loop.create_connection(_GeneralProtocol, ip, tcp_port, local_addr=local_addr)
    t.write(_get_sendready_data("_check_if_id_is_available", _id = randomname.generate()))
    LOG.debug(f"Client listen on address {local_addr}(TCP/UDP)")

async def start_server(ip: str, tcp_port: int, udp_port: int, network_listener: NetworkListener):
    # Assign global variables listed below
    global listener, udp_connection, server
    listener = network_listener
    loop = asyncio.get_running_loop()
    t, p = await loop.create_datagram_endpoint(_GeneralDatagramProtocol, local_addr=(ip, udp_port))
    udp_connection = UDPConnection(t, p)
    server = await loop.create_server(_GeneralProtocol, ip, tcp_port)
    LOG.debug(f"Server listen on address {ip}:{tcp_port}(TCP):{udp_port}(UDP)")

def send(action: str, data = None, to: str = None):
    LOG.debug(f"Sending TCP action '{action}' to {to if to else "all"}")
    if to:
        conn = tcp_connections.get(to)
        if conn:
            conn.transport.write(_get_sendready_data(action, data, to))
        else:
            LOG.warning(f"Could not send message to {to}. No such connection.")
    else:
        for to, connection in tcp_connections.items():
            connection.transport.write(_get_sendready_data(action, data, to))
        

def send_udp(action: str, data = None, to: str = None):
    if not udp_connection: return
    if to:
        conn = tcp_connections.get(to)
        if conn:
            udp_connection.transport.sendto(_get_sendready_data(action, data, to), conn.udp_address)
        else:
            LOG.warning(f"Could not send message to {to}. No such connection.")
    else:
        for to, connection in tcp_connections.items():
            udp_connection.transport.sendto(_get_sendready_data(action, data, to), connection.udp_address)
        

def is_connected(_id: str) -> bool:
    conn = tcp_connections.get(_id)
    return conn and not conn.transport.is_closing()

def close():
    """ Resets global variables and closes all connections. """
    # Prepare for deletion and delete global references listed below
    global server, tcp_connections, udp_connection, listener
    if server:
        server.close()
    for connection in tcp_connections.values():
        connection.transport.write_eof()
    server = None
    tcp_connections.clear()
    udp_connection = None
    listener = None
    LOG.debug("All connections have been closed.")

    
class ContextManager:
    def __enter__(self): pass
    def __exit__(self, exc_type, exc_value, traceback): close()