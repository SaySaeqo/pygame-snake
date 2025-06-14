import asyncio
import socket
import typing

async def first_completed(*coroutines) -> typing.Optional[typing.Any]:
    try:
        tasks = [asyncio.create_task(c) for c in coroutines]
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        return done.pop().result()
    except Exception as e:
        raise e
    finally:
        for task in tasks:
            task.cancel()

def find(list, key) -> typing.Any:
    if callable(key):
        return next(x for x in list if key(x))
    return next(x for x in list if key == x)

def find_index(list, key) -> int:
    if callable(key):
        return next(i for i, x in enumerate(list) if key(x))
    return next(i for i, x in enumerate(list) if key == x)

def get_my_ip() -> str:
    local_hostname = socket.gethostname()

    # Step 2: Get a list of IP addresses associated with the hostname.
    ip_addresses = socket.gethostbyname_ex(local_hostname)[2]

    # Step 3: Filter out loopback addresses (IPs starting with "127.").
    filtered_ips = [ip for ip in ip_addresses if not ip.startswith("127.")]

    # Step 4: Extract the first IP address (if available) from the filtered list.
    first_ip = filtered_ips[:1]

    return first_ip[0] if first_ip else None

def singleton(cls):
    """It is a class decorator"""
    instance=cls()
    cls.__new__ = cls.__call__= lambda cls: instance
    cls.__init__ = lambda self: None
    return instance