# gamenetwork - lighweight multiplayer networking library
Gamenetwork is lightweight library to be used mostly with pygame, but can work also in other scenarios.  
It assumes that there will be not more than one server or client running per python instance so connections for simplicity of usage are made global variables.  
Simply usage predicts connecting to the server (or creating one), sending action-based messages and closing connections before exit.  

# example code usage

```python
# server.py
import gamenetwork as net
import asyncio

async def main():

    running = asyncio.get_running_loop().create_future()

    class Server(net.NetworkListener):

        def action_hello(self, data):
            print(f"Doing sth with data: {data}")
            net.send("response", data.upper())

        def action_stop(self, data):
            running.set_result("done!")

        def connected(self):
            print("I am connected <3")

        def disconnected(self):
            print("Noooo :<")

    with net.ContextManager():
        await net.start_server("0.0.0.0", 1234, 1234, Server(address))
        await running

asyncio.run(main())

# client.py
import gamenetwork as net
import asyncio

async def main():

    running = asyncio.get_running_loop().create_future()
    
    def send_input():
        text = input("You: ")
        if text:
            net.send("hello", text)
        else:
            net.send("stop")
            running.set_result("done!")

    class Client(net.NetworkListener):

        def action_response(self, data):
            print(f"Response: {data}")
            send_input()

        def connected(self):
            print("I am connected <3")

        def disconnected(self):
            print("Noooo :<")

    with net.ContextManager():
        await net.connect_to_server("localhost", 1234, 1234, Client(address))
        send_input()
        await running
    
asyncio.run(main())
