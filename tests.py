import network
import unittest
import asyncio
import logging

logging.basicConfig(level=logging.INFO)


async def test(clientOrServer: str):

    def after_disconnect(who: network.NetworkAddress):
        ...

    async def while_connecting():
        while True:
            await asyncio.sleep(1)

    address = network.NetworkAddress("localhost", 1234)

    def get_initial_data(who: network.NetworkAddress):
        return b"."
    
    async def server_main():
        while True:
            t = input("Give me that! ")
            await asyncio.sleep(1)
            if t == "q":
                break

    async def client_main():
        while True:
            await asyncio.sleep(1)


    def get_server_dataflow_function(phase):
        def server_dataflow(data, addr):
            input = f"From client phase {phase}"
            output = f"From server phase {phase}"
            
            assert data == network.simple2bytes(input)
            return network.simple2bytes(output)
        return server_dataflow
    
    def get_client_dataflow_function(phase):
        def client_dataflow(data):
            input = f"From server phase {phase}"
            output = f"From client phase {phase}"
            
            assert data == network.simple2bytes(input)
            return network.simple2bytes(output)
        return client_dataflow
    
    server_phases = [
        network.NetworkPhase(get_server_dataflow_function(i), server_main()) for i in range(2)
    ]
    
    client_phases = [
        network.NetworkPhase(get_client_dataflow_function(i), client_main()) for i in range(2)
    ]

    
    if clientOrServer == "s":
        await network.run_server(address, server_phases, after_disconnect, get_initial_data)
    elif clientOrServer == "c":
        await network.run_client(address, client_phases, while_connecting())
    else:
        raise ValueError("Invalid input")




        


if __name__ == "__main__":

    test_side = input("Test server or client? c/s ")
    asyncio.run(test(test_side))