from dataclasses import dataclass
import asyncio
import json
from typing import Coroutine
from utils import *
import logging
from enum import Enum
from icecream import ic

log = logging.getLogger(__name__)

@dataclass
class NetworkAddress:
    ip: str = "localhost"
    port: int = 0

    def to_json(self):
        return {
            "ip": self.ip,
            "port": self.port
        }
    
    @classmethod
    def from_json(cls, json):
        return cls(json["ip"], json["port"])
    
    def __repr__(self) -> str:
        return f"{self.ip}:{self.port}"

@dataclass
class Player:
    name: str
    address: NetworkAddress

    def to_json(self):
        return {
            "name": self.name,
            "address": self.address.to_json() if self.address else None
        }
    
    @classmethod
    def from_json(cls, json):
        return cls(json["name"], NetworkAddress.from_json(json["address"]) if json["address"] else None)
        

async def sendCounted(writer: asyncio.StreamWriter, bytes: bytes):
    writer.write(len(bytes).to_bytes(10))
    await writer.drain()
    writer.write(bytes)
    await writer.drain()

async def readCounted(reader: asyncio.StreamReader) -> bytes:
    data_len = int.from_bytes(await reader.read(10))
    return await reader.read(data_len)

def simple2bytes(data) -> bytes:
    return json.dumps(data).encode()

def bytes2simple(data: bytes):
    return json.loads(data)

SHORTSIMPLE_MAXLEN = 32

async def writeShortSimple(writer: asyncio.StreamWriter, data):
    data = simple2bytes(data)
    if len(data) > SHORTSIMPLE_MAXLEN:
        raise ValueError(f"Data is too long: {len(data)}")
    writer.write(data)
    await writer.drain()

async def readShortSimple(reader: asyncio.StreamReader):
    return bytes2simple(await reader.read(SHORTSIMPLE_MAXLEN))


@dataclass
class NetworkPhase:
    dataflow: callable
    main: Coroutine


# Data frame structure will be: PHASE_NUMBER | DATA_LEN | DATA
    
DATALEN_BYTES = 8
PHASENUMBER_BYTES = 2
async def readDataFrame(reader: asyncio.StreamReader) -> tuple[bytes, int]:
    header = await reader.read(PHASENUMBER_BYTES + DATALEN_BYTES)
    phase, data_len = header[:PHASENUMBER_BYTES], header[PHASENUMBER_BYTES:]
    phase, data_len = int.from_bytes(phase), int.from_bytes(data_len)
    data = await reader.read(data_len)
    return data, phase

async def writeDataFrame(writer: asyncio.StreamWriter, data: bytes, phase: int):
    writer.write(phase.to_bytes(PHASENUMBER_BYTES))
    writer.write(len(data).to_bytes(DATALEN_BYTES))
    writer.write(data)
    await writer.drain()


async def run_server(address: NetworkAddress, phases: list[NetworkPhase], after_disconnected: callable, get_initial_data: callable):
    """
        Caution: phases should strictly correspond to the client's phases as client phase input is server's output and vice versa.
    """
    CURRENT_PHASE = 0

    async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        nonlocal CURRENT_PHASE
        try:
            addr = writer.get_extra_info('peername')
            addr = NetworkAddress(addr[0], addr[1])
            log.info(f"Connected with {addr}")
            phase_num = CURRENT_PHASE
            data = get_initial_data(addr)
            while data:
                await writeDataFrame(writer, data, CURRENT_PHASE)
                data, phase_num  = await readDataFrame(reader)
                data = phases[phase_num].dataflow(data, addr)
                    
        except ConnectionError as e:
            log.error(e)
        finally:
            log.info(f"Disconnected with {addr}")
            writer.close()
            after_disconnected(addr)

    server = await asyncio.start_server(handle_client, address.ip, address.port)

    async with server:
        serving = asyncio.create_task(server.serve_forever())

        for phase in phases:
            log.info(f"Phase {CURRENT_PHASE}")
            await phase.main
            CURRENT_PHASE += 1
            serving.cancel()


async def run_client(host: NetworkAddress, phases: list[NetworkPhase], while_connecting: Coroutine):
    """
        Caution: phases should strictly correspond to the server's phases as client phase input is server's output and vice versa.
    """

    try:
        connection = await first_completed(asyncio.open_connection(host.ip, host.port), while_connecting)
        if not (isinstance(connection, tuple) and isinstance(connection[0], asyncio.StreamReader) and isinstance(connection[1], asyncio.StreamWriter)):
            log.info("Connection aborted")
            return
    except OSError as e:
        log.error(e)
        log.info("Could not connect to the server")
        return
    reader, writer = connection
    log.info("Connected to the server")

    NEXT_PHASE = 0
    CONNECTION_LOST = 1

    def get_handler(phase: NetworkPhase):
        async def handler():
            try:
                this_phase_num = None
                data = "."
                while data:
                    data, phase_num = await readDataFrame(reader)
                    data = phase.dataflow(data)
                    if this_phase_num is None:
                        this_phase_num = phase_num
                        log.info(f"Phase {this_phase_num}")

                    await writeDataFrame(writer, data, this_phase_num)

                    if phase_num != this_phase_num:
                        return NEXT_PHASE
            except ConnectionError as e:
                log.error(e)

            return CONNECTION_LOST
           
        return handler()

    for phase in phases:
        result = await first_completed(get_handler(phase), phase.main)
        if result != NEXT_PHASE:
            break

    writer.close()
    log.info("Disconnected with a server")
