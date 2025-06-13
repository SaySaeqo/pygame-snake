import facade as net
import sys
import logging
import asyncio

LOG = logging.getLogger("server_tester")


class ServerTester(net.NetworkListener):
    def action_send_udp(self, data):
        net.send_udp("print", f"Got UDP data from server! {data=}", self._id)
    def action_send_udp_to_all(self, data):
        net.send_udp("print", f"Got UDP data from server! {data=}")
    def action_send_direct_udp(self, data):
        net.udp_connection.transport.sendto(net._get_sendready_data("print", f"Got direct UDP data from server! {data=}"), self._address)
    def action_send_tcp(self, data):
        net.send("print", f"Got TCP data from server! {data=}", self._id)
    def action_send_tcp_to_all(self,data):
        net.send("print", f"Got TCP data from server! {data=}")
    def action_send_direct_tcp(self, data):
        self.transport.write(net._get_sendready_data("print", f"Got direct TCP data from server! {data=}"))
    def action_get_logs(self, num_of_last_lines):
        with open("server_tester.log") as file:
            net.send("print", "\n".join(file.readlines()[-num_of_last_lines:]))
    def action_set_logging_level(self, level):
        LOG.setLevel(level)
    def action_terminate(self, data):
        net.close()


async def main():
    if len(sys.argv) != 3:
        LOG.warning("Use: python server_tester.py <tcp_port> <udp_port>")
        sys.exit()

    logging.basicConfig(level=logging.DEBUG)
    # logging.basicConfig(level=logging.DEBUG, filename="server_tester.log", filemode="w")
    with net.ContextManager():
        name, tcp_port, udp_port = sys.argv
        await net.start_server("0.0.0.0", tcp_port, udp_port, ServerTester())
        await net.server.wait_closed()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        ...

