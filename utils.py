import sys
from typing import Callable, Hashable, List, Optional, Sequence, TypeVar
import asyncio
import socket

if sys.version_info < (3, 6):
    from collections import OrderedDict as _OrderedDict
else:
    # starting from Python3.6 `dict`s are insertion ordered by default
    _OrderedDict = dict

_T = TypeVar('_T')


def unique(values: Sequence[_T],
           key: Optional[Callable[[_T], Hashable]] = None) -> List[_T]:
    """
    Returns unique values by given key (using value itself by default)
    preserving order (taking first-from-start occurrence).

    Time complexity: O(len(values))
    Memory complexity: O(len(values

    >>> unique([-1, 1, 0, 1])
    [-1, 1, 0]
    >>> unique([-1, 1, 0, 1], key=abs)
    [-1, 0]
    """
    return sorted(
        list(
            _OrderedDict.fromkeys(values)
            if key is None
            else _OrderedDict((key(value), value)
                              for value in reversed(values)).values()
    ), key=values.index)


async def first_completed(*coroutines):
    try:
        tasks = [asyncio.create_task(c) for c in coroutines]
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        return done.pop().result()
    except Exception as e:
        raise e
    finally:
        for task in tasks:
            task.cancel()

def find(list, key):
    if callable(key):
        return next(x for x in list if key(x))
    return next(x for x in list if key == x)

def find_index(list, key):
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
