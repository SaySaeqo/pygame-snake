# Run this script on some server and then run one of client scripts on your pc

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
    @net.udp_only
    def action_send_direct_udp(self, data):
        net.udp_connection.transport.sendto(net._get_sendready_data("print", f"Got direct UDP data from server! {data=}", self._id), self._address)
    def action_send_tcp(self, data):
        net.send("print", f"Got TCP data from server! {data=}", self._id)
    def action_send_tcp_to_all(self,data):
        net.send("print", f"Got TCP data from server! {data=}")
    @net.tcp_only
    def action_send_direct_tcp(self, data):
        self.transport.write(net._get_sendready_data("print", f"Got direct TCP data from server! {data=}", self._id))
    def action_get_logs(self, num_of_last_lines):
        with open("server_tester.log") as file:
            try: 
                num = int(num_of_last_lines)
            except ValueError:
                num = 10
            net.send("print", "\n".join(file.readlines()[-num:]))
    def action_set_logging_level(self, level):
        LOG.setLevel(level)
    def action_terminate(self, data):
        net.close()


async def main():
    logging.basicConfig(level=logging.DEBUG, filename="server_tester.log", filemode="w")
    
    if len(sys.argv) != 3:
        LOG.warning("Use: python server_tester.py <tcp_port> <udp_port>")
        sys.exit()
        
    with net.ContextManager():
        name, tcp_port, udp_port = sys.argv
        tcp_port = int(tcp_port)
        udp_port = int(udp_port)
        await net.start_server("0.0.0.0", tcp_port, udp_port, ServerTester())
        print("Server has been started.")
        await net.server.wait_closed()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        ...

