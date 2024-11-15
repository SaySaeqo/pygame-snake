import unittest
from .facade import *
import asyncio
import logging

class FailEndPointTestCase(unittest.IsolatedAsyncioTestCase):
    async def runTest(self):
        try:
            await connect_to_server(NetworkAddress("localhost", 31429))
        except OSError as osError:
            return
        self.fail("Expected OSError")

class EndPointTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.outgoing = [
            {"action": "hello", "data": {"a": 321, "b": [2, 3, 4], "c": ["afw", "wafF", "aa", "weEEW", "w234r"], "d": ["x"] * 256}},
            {"action": "hello", "data": [454, 35, 43, 543, "aabv"]},
            {"action": "hello", "data": [10] * 512},
            #{"action": "hello", "data": [10] * 512, "otherstuff": "hello\0---\0goodbye", "x": [0, "---", 0], "y": "zÃ¤Ã¶"},
        ]
        self.count = len(self.outgoing)
        self.lengths = [len(data['data']) for data in self.outgoing]

        class TesterData:
            def __init__(self):
                self.received = []
                self.count = 0
                self.connected = False

        self.serverTester_data = serverData = TesterData()
        self.endpointTester_data = endpointData = TesterData()
        
        class ServerTester(NetworkListener):
            def Network_connected(self):
                serverData.connected = True

            def Network_hello(self, data):
                serverData.received.append(data)
                serverData.count += 1
                self.conn.send("gotit", "Yeah, we got it: " + str(len(data)) + " elements")

            def Network_disconnected(self):
                serverData.connected = False
        
        class EndPointTester(NetworkListener):
            def Network_connected(self):
                endpointData.connected = True
            
            def Network_gotit(self, data):
                endpointData.received.append(data)
                endpointData.count += 1

            def Network_disconnected(self):
                endpointData.connected = False
        
        server_adress = NetworkAddress("localhost", 31426)
        await start_server(server_adress, lambda conn: ServerTester(conn))
        self.endpoint = await connect_to_server(server_adress, lambda conn: EndPointTester(conn))
        del connections[server_adress]
    
    async def runTest(self):
        self.endpoint: EndPoint
        for o in self.outgoing:
            self.endpoint.send(o["action"], o["data"])

        await asyncio.sleep(.1)
        
        self.assertTrue(self.serverTester_data.connected, "Server is not connected")
        self.assertTrue(self.endpointTester_data.connected, "Endpoint is not connected")

        self.assertTrue(self.serverTester_data.count == self.count, f"Didn't receive the right number of messages. Expected {self.count}, got {self.serverTester_data.count}")
        self.assertTrue(self.endpointTester_data.count == self.count, f"Didn't receive the right number of messages. Expected {self.count}, got {self.endpointTester_data.count}")   
        
        # see if what we receive from the server is what we expect
        for r in self.serverTester_data.received:
            expected = self.outgoing.pop(0)["data"]
            self.assertTrue(r == expected, str(r) + " =/= " + str(expected))
        self.serverTester_data.received = []
        
        # see if what we receive from the client is what we expect
        for r in self.endpointTester_data.received:
            expected = "Yeah, we got it: %d elements" % self.lengths.pop(0)
            self.assertTrue(r == expected, str(r) + " =/= " + str(expected))
        self.endpointTester_data.received = []
            

        del self.endpoint
        await asyncio.sleep(0.1)
        await asyncio.sleep(0.1)
        await asyncio.sleep(0.1)
        self.assertFalse(self.serverTester_data.connected, "Server did not get disconnected event from endpoint")

    async def asyncTearDown(self):
        close()



if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("asyncio").setLevel(logging.INFO)
    unittest.main()