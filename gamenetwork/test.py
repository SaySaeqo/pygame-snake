# Run as: 'python -m gamenetwork.test' from parent folder 

import unittest

# import facade twice as client and server
import sys
from . import facade as server
names = [_ for _ in sys.modules if _.startswith(__package__)]
for n in names: del sys.modules[n]
from . import facade as client
assert client != server
#

import asyncio
import logging
import toolz
from icecream import ic

LOG = logging.getLogger("test")

class DataTransform(unittest.TestCase):
    def runTest(self):
        senddata = server._get_sendready_data("hello", [1, 2, 3, 4, 5])
        self.assertIsInstance(senddata, bytes, "get_sendready_data does not return bytes")
        senddata = senddata + b"hello"
        senddata = senddata + server._get_sendready_data("hello", [1, 2, 3, 4, 5])
        readdata = server._get_readready_data_generator(senddata)
        for d in readdata:
            self.assertEqual(d["action"], "hello", "Action is not hello")
            self.assertEqual(d["data"], [1, 2, 3, 4, 5], "Data is not [1, 2, 3, 4, 5]")
        self.assertIsInstance(senddata, bytes, "get_readready_data_generator is not pure")

class DataDistribution(unittest.TestCase):
    
    def runTest(self):
        senddata = server._get_sendready_data("hello", [1, 2, 3, 4, 5])
        senddata = senddata + b"hello"
        senddata = senddata + server._get_sendready_data("hello", [1, 2, 3, 4, 5])

        server.listener = server.NetworkListener()
        server._distribute_data(senddata, None)
        self.assertIsInstance(senddata, bytes, "distribute_data is not pure")
        server.listener = None

class FailedToConnect(unittest.IsolatedAsyncioTestCase):
    async def runTest(self):
        server.LOG.setLevel(logging.WARNING)
        client.LOG.setLevel(logging.WARNING)
        LOG.setLevel(logging.WARNING)
        try:
            await client.connect_to_server("localhost", 31429, 31429, client.NetworkListener())
        except OSError as osError:
            return
        finally:
            client.close()
        self.fail("Expected OSError")


class EndPoint(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        server.LOG.setLevel(logging.WARNING)
        client.LOG.setLevel(logging.WARNING)
        LOG.setLevel(logging.WARNING)

        self.outgoing = [
            {"action": "hello", "data": {"a": 321, "b": [2, 3, 4], "c": ["afw", "wafF", "aa", "weEEW", "w234r"], "d": ["x"] * 256}},
            {"action": "hello", "data": [454, 35, 43, 543, "aabv"]},
            {"action": "hello", "data": [10] * 512},
            #{"action": "hello", "data": [10] * 512, "otherstuff": "hello\0---\0goodbye", "x": [0, "---", 0], "y": "zÃ¤Ã¶"},
        ]
        self.count = len(list(toolz.unique(self.outgoing, lambda x: x["action"])))
        self.lengths = [len(data['data']) for data in self.outgoing]

        class TesterData:
            def __init__(self):
                self.received = []
                self.count = 0
                self.connected = False

        self.serverTester_data = serverData = TesterData()
        self.endpointTester_data = endpointData = TesterData()
        
        class ServerTester(server.NetworkListener):
            def connected(self):
                serverData.connected = True

            def action_hello(self, data):
                serverData.received.append(data)
                serverData.count += 1
                server.send("gotit", "Yeah, we got it: " + str(len(data)) + " elements")

            def disconnected(self):
                serverData.connected = False
        
        class EndPointTester(client.NetworkListener):
            def connected(self):
                endpointData.connected = True
            
            def action_gotit(self, data):
                endpointData.received.append(data)
                endpointData.count += 1

            def disconnected(self):
                endpointData.connected = False
        
        self.endpoint_tester = EndPointTester
        self.ports = (31429, 31429)
        await server.start_server("0.0.0.0", *self.ports, ServerTester())
        await client.connect_to_server("localhost", *self.ports, EndPointTester())
    
    async def runTest(self):
        
        self.assertTrue(self.serverTester_data.connected, "Server is not connected")
        self.assertTrue(self.endpointTester_data.connected, "Endpoint is not connected")

        for o in self.outgoing:
            client.send(o["action"], o["data"])

        await asyncio.sleep(.01)

        self.assertTrue(self.serverTester_data.count == self.count, f"Server have not received the right number of messages. Expected {self.count}, got {self.serverTester_data.count}")
        self.assertTrue(self.endpointTester_data.count == self.count, f"Endpoint have not received the right number of messages. Expected {self.count}, got {self.endpointTester_data.count}")   
        
        # see if what we receive from the server is what we expect
        for r in self.serverTester_data.received:
            expected = self.outgoing.pop(0)["data"]
            self.assertTrue(r == expected, f"{r} =/= {expected}")
        self.serverTester_data.received = []
        
        # see if what we receive from the client is what we expect
        for r in self.endpointTester_data.received:
            expected = f"Yeah, we got it: {self.lengths.pop(0)} elements"
            self.assertTrue(r == expected, f"{r} =/= {expected}")
        self.endpointTester_data.received = []
            

        client.close()
        await asyncio.sleep(0.01)
        
        self.assertFalse(self.serverTester_data.connected, "Server have not got disconnected event from endpoint")
        self.assertFalse(self.endpointTester_data.connected, "Endpoint have not got disconnected event from server")

        await client.connect_to_server("localhost", *self.ports, self.endpoint_tester())
        await asyncio.sleep(0.01)

        self.assertTrue(self.serverTester_data.connected, "Server could not reconnected")
        self.assertTrue(self.endpointTester_data.connected, "Endpoint could not reconnected")


    async def asyncTearDown(self):
        LOG.info("Closing EndPoint test.")
        server.close()
        client.close()

class UDPEndPoint(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        server.LOG.setLevel(logging.WARNING)
        client.LOG.setLevel(logging.WARNING)
        LOG.setLevel(logging.WARNING)
        self.ports = (40000, 40010)

        self.server_data = server_data = { "arrived": False }
        self.client_data = client_data = { "arrived": False }

        class HolePunchingListener(server.NetworkListener):
            def action__hole_punching(self, data):
                server_data["arrived"] = True

        class ClientHolePunchingListener(client.NetworkListener):
            def action__hole_punching(self, data):
                client_data["arrived"] = True

        await server.start_server("0.0.0.0", *self.ports, HolePunchingListener())
        await client.connect_to_server("localhost", *self.ports, ClientHolePunchingListener())

    async def runTest(self):
        await asyncio.sleep(2.1) # enough for 3 holepunching actions per side
        
        self.assertTrue(self.server_data["arrived"], "Server have not got holepunching message.")
        self.assertTrue(self.client_data["arrived"], "Client have not got holepunching message.")

    async def asyncTearDown(self):
        LOG.info("Closing UDP test")
        server.close()
        client.close()



if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    server.LOG = logging.getLogger("server")
    client.LOG = logging.getLogger("client")
    unittest.main()