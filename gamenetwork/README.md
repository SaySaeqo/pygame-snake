# gamenetwork - lighweight multiplayer networking library
Gamenetwork is lightweight library to be used mostly with pygame, but can work also in other scenarios.  
It assumes that there will be not more than one server or client running per python instance so connections for simplicity of usage are made global variables.  
Simply usage predicts connecting to the server (or creating one) by ip-port tuple, sending action-based messages and closing connections before exit.

# example code usage

```python
# server.py
import gamenetwork as net
import asyncio

async def main():

    running = True

    class Server(net.NetworkListener):

        def action_hello(self, data):
            print(f"Doing sth with data: {data}")
            net.send("response", data.upper())

        def action_stop(self, data):
            nonlocal running
            running = False

        def connected(self):
            print("I am connected <3")

        def disconnected(self):
            print("Noooo :<")

    try:
        await net.start_server((None, 1234), lambda address: Server(address))
        while running:
            await asyncio.sleep(0.1)
    finally:
        net.close()

asyncio.run(main())

# client.py
import gamenetwork as net
import asyncio

async def main():

    running = True
    def get_input():
        text = input("You: ")
        if text:
            net.send("hello", text)
        else:
            net.send("stop")
            nonlocal running
            running = False

    class Client(net.NetworkListener):

        def action_response(self, data):
            print(f"Response: {data}")
            get_input()

        def connected(self):
            print("I am connected <3")

        def disconnected(self):
            print("Noooo :<")

    try:
        await net.connect_to_server(("localhost", 1234), lambda address: Client(address))
        get_input()
        while running:
            await asyncio.sleep(0.1)
    finally:
        net.close()
    
asyncio.run(main())
