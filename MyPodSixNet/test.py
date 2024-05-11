import unittest
import logging
from endpoint import EndPoint
from server import Server
from helpers import NetworkListener, NetworkAddress
from tobeused import connect_to_server, start_server
from time import time, sleep

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

class FailEndPointTestCase(unittest.IsolatedAsyncioTestCase):
    async def runTest(self):
        try:
            await connect_to_server(NetworkAddress("localhost", 31429))
        except OSError as osError:
            return
        self.fail("Expected OSError")

class EndPointTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.outgoing = [
            {"action": "hello", "data": {"a": 321, "b": [2, 3, 4], "c": ["afw", "wafF", "aa", "weEEW", "w234r"], "d": ["x"] * 256}},
            {"action": "hello", "data": [454, 35, 43, 543, "aabv"]},
            {"action": "hello", "data": [10] * 512},
            #{"action": "hello", "data": [10] * 512, "otherstuff": "hello\0---\0goodbye", "x": [0, "---", 0], "y": "zÃ¤Ã¶"},
        ]
        self.count = len(self.outgoing)
        self.lengths = [len(data['data']) for data in self.outgoing]
        
        class ServerChannel(Channel):
            def Network_hello(self, data):
                self._server.received.append(data)
                self._server.count += 1
                self.Send({"action": "gotit", "data": "Yeah, we got it: " + str(len(data['data'])) + " elements"})
        
        class TestEndPoint(EndPoint):
            received = []
            connected = False
            count = 0
            
            def Network_connected(self, data):
                self.connected = True
            
            def Network_gotit(self, data):
                self.received.append(data)
                self.count += 1
                
        
        class TestServer(Server):
            connected = False
            received = []
            count = 0
            
            def Connected(self, channel, addr):
                self.connected = True
        
        self.server = TestServer(channelClass=ServerChannel, localaddr=("127.0.0.1", 31426))
        self.endpoint = TestEndPoint(("127.0.0.1", 31426))
    
    def runTest(self):
        self.endpoint.DoConnect()
        for o in self.outgoing:
            self.endpoint.Send(o)
        
        
        for x in range(50):
            self.server.Pump()
            self.endpoint.Pump()
            
            # see if what we receive from the server is what we expect
            for r in self.server.received:
                self.assertTrue(r == self.outgoing.pop(0))
            self.server.received = []
            
            # see if what we receive from the client is what we expect
            for r in self.endpoint.received:
                self.assertTrue(r['data'] == "Yeah, we got it: %d elements" % self.lengths.pop(0))
            self.endpoint.received = []
            
            sleep(0.001)
        
        self.assertTrue(self.server.connected, "Server is not connected")
        self.assertTrue(self.endpoint.connected, "Endpoint is not connected")
        
        self.assertTrue(self.server.count == self.count, "Didn't receive the right number of messages")
        self.assertTrue(self.endpoint.count == self.count, "Didn't receive the right number of messages")
        
        self.endpoint.Close()
        
    
    def tearDown(self):
        del self.server
        del self.endpoint



if __name__ == '__main__':
    unittest.main()