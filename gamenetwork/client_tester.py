import facade as net
import sys
import logging
import asyncio

LOG = logging.getLogger("client_tester")

class ClientTester(net.NetworkListener):
    def action_print(self, data):
        print(f"Response: {data}")

async def main():

    if len(sys.argv) != 4:
        LOG.warning("Use: python client_tester.py <server_ip> <tcp_port> <udp_port>")
        sys.exit()
    name, ip, tcp_port, udp_port = sys.argv

    with net.ContextManager():
        await net.connect_to_server(ip, tcp_port, udp_port, ClientTester())

        print("Write action to send tcp action to server."
              "> Add 'udp_' prefix to send UDP action."
              "> Write 'const_data' to remember once entered data."
              "> Leave action blank to send again the same action."
              "> Use action 'q' to quit this client.")

        action = None
        data = None
        const_data = False
        prev_action = None
        while action != "terminate":
            prev_action = action
            action = input("Action: ")
            if action == "q": return
            if not const_data:
                data = input("Data: ")

            if action == "":
                action = prev_action

            if action == "const_data":
                const_data = not const_data
            elif action.startswith("udp_"):
                net.send_udp(action.removeprefix("udp_"), data)
                LOG.info(f"UDP action '{action}' has been sended.")
            else:
                net.send(action, data)
                LOG.info(f"TCP action '{action}' has been sended.")
            await asyncio.sleep(0.1)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())