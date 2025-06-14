# run as: 'python -m gamenetwork.test' from parent folder 

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
        try:
            await client.connect_to_server("localhost", 31429, 31429, client.NetworkListener())
        except OSError as osError:
            return
        finally:
            client.close()
        self.fail("Expected OSError")

class EndPointTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
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
        self.server_adress = ("localhost", 31429, 31429)
        await server.start_server(*self.server_adress, ServerTester())
        await client.connect_to_server(*self.server_adress, EndPointTester())
    
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

        await client.connect_to_server(*self.server_adress, self.endpoint_tester())
        await asyncio.sleep(0.01)

        self.assertTrue(self.serverTester_data.connected, "Server could not reconnected")
        self.assertTrue(self.endpointTester_data.connected, "Endpoint could not reconnected")


    async def asyncTearDown(self):
        LOG.info("Closing test.")
        server.close()
        client.close()



if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("asyncio").setLevel(logging.INFO)
    server.LOG = logging.getLogger("server")
    client.LOG = logging.getLogger("client")
    unittest.main()