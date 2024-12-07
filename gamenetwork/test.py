import unittest
from .facade import *
import asyncio
import logging

class DataTransformTestCase(unittest.TestCase):
    def runTest(self):
        senddata = get_sendready_data("hello", [1, 2, 3, 4, 5])
        self.assertIsInstance(senddata, bytes, "get_sendready_data does not return bytes")
        senddata = senddata + b"hello"
        senddata = senddata + get_sendready_data("hello", [1, 2, 3, 4, 5])
        readdata = get_readready_data_generator(senddata)
        for d in readdata:
            self.assertEqual(d["action"], "hello", "Action is not hello")
            self.assertEqual(d["data"], [1, 2, 3, 4, 5], "Data is not [1, 2, 3, 4, 5]")
        self.assertIsInstance(senddata, bytes, "get_readready_data_generator is not pure")

class DataDistributionTestCase(unittest.TestCase):
    
    def runTest(self):
        senddata = get_sendready_data("hello", [1, 2, 3, 4, 5])
        senddata = senddata + b"hello"
        senddata = senddata + get_sendready_data("hello", [1, 2, 3, 4, 5])

        distribute_data(senddata, NetworkListener(("localhost", 31425)))
        self.assertIsInstance(senddata, bytes, "distribute_data is not pure")
        

class FailEndPointTestCase(unittest.IsolatedAsyncioTestCase):
    async def runTest(self):
        try:
            await connect_to_server(("localhost", 31429))
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
        self.count = 1
        self.lengths = [len(data['data']) for data in self.outgoing]

        class TesterData:
            def __init__(self):
                self.received = []
                self.count = 0
                self.connected = False

        self.serverTester_data = serverData = TesterData()
        self.endpointTester_data = endpointData = TesterData()
        
        class ServerTester(NetworkListener):
            def connected(self):
                serverData.connected = True

            def action_hello(self, data):
                serverData.received.append(data)
                serverData.count += 1
                send("gotit", "Yeah, we got it: " + str(len(data)) + " elements", to=self.address)

            def disconnected(self):
                serverData.connected = False
        
        class EndPointTester(NetworkListener):
            def connected(self):
                endpointData.connected = True
            
            def action_gotit(self, data):
                endpointData.received.append(data)
                endpointData.count += 1

            def disconnected(self):
                endpointData.connected = False
        
        server_adress = ("localhost", 31426)
        await start_server(server_adress, lambda address: ServerTester(address))
        await connect_to_server(server_adress, lambda address: EndPointTester(address))
        self.sender = connections.pop(server_adress)
    
    async def runTest(self):
        for o in self.outgoing:
            self.sender[0].write(get_sendready_data(o["action"], o["data"]))

        await asyncio.sleep(.01)
        
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
            

        self.sender[0].abort()
        await asyncio.sleep(0.01)
        
        self.assertFalse(self.serverTester_data.connected, "Server did not get disconnected event from endpoint")

    async def asyncTearDown(self):
        close()



if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("asyncio").setLevel(logging.INFO)
    unittest.main()