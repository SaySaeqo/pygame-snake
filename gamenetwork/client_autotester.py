import facade as net
import logging
import asyncio
import unittest

LOG = logging.getLogger("client_autotester")

class MyTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.test_data = test_data = {"count": 0, "future": None}
        class ClientTester(net.NetworkListener):
            def action_print(self, data):
                test_data["count"] = test_data["count"] + 1
                if test_data["future"]:
                    test_data["future"].set_result(data)

        IP, TCP_PORT, UDP_PORT = "192.168.0.143", 3000, 3100
        await net.connect_to_server(IP, TCP_PORT, UDP_PORT, ClientTester())

    async def runTest(self):

        actions = [
            "send_udp", "send_udp_to_all", "send_direct_udp",
            "send_tcp", "send_tcp_to_all", "send_direct_tcp",
        ]

        await asyncio.sleep(2.1) # Some time for UDP connection to bond for sure

        loop = asyncio.get_running_loop()

        TESTS_TO_PASS = 10
        count = 0

        for action in actions:
            if action != "send_direct_udp":
                self.test_data["future"] = loop.create_future()
                net.send(action, "some_data")
                await self.test_data["future"]
                count += 1
                print(f"TESTS PASSED: [{"▮"*count + " "*(TESTS_TO_PASS-count)}]", end="\r")
        for action in actions:
            if action != "send_direct_tcp":
                self.test_data["future"] = loop.create_future()
                net.send_udp(action, "some_data")
                await self.test_data["future"]
                count += 1
                print(f"TESTS PASSED: [{"▮"*count + " "*(TESTS_TO_PASS-count)}]", end="\r")

        future = loop.create_future()
        self.test_data["future"] = future
        net.send("get_logs", 30)
        print(await future)
        LOG.info(f"Server logs: {future.result()}")

    async def asyncTearDown(self):
        LOG.info("Closing test.")
        net.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    unittest.main()