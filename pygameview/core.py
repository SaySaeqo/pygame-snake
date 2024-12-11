import pygame
import sys
import logging
import asyncio
import typing

DEFAULT_FPS = 60

class AsyncClock:
    def __init__(self, time_func=pygame.time.get_ticks):
        self.time_func = time_func
        self.last_tick = time_func() or 0
 
    async def tick(self, fps=0) -> float:
        """
        It is not perfect 1/fps long tick, can be around this number, especially for windows
        """
        if 0 >= fps:
            return

        since_last_tick = self.time_func() - self.last_tick
        to_await = (1.0 / fps) * 1000
        delay = (to_await - since_last_tick) / 1000

        await asyncio.sleep(delay)
        now = self.time_func()
        awaited = (now - self.last_tick) / 1000
        self.last_tick = now
        return awaited

class PyGameView:

    def update(self, delta):
        pass

    def handle_event(self, event):
        if (event.type == pygame.QUIT):
            sys.exit()

    async def do_async(self):
        pass

    def __await__(self):
        return run_async(self).__await__()

_current_view: PyGameView = None
_closing = False

def current_view() -> typing.Optional[PyGameView]:
    """
    Returns the current view that is being displayed.
    """
    global _current_view
    return _current_view

def current_view_name() -> str:
    return current_view().__class__.__name__ if _current_view else None

def set_view(view):
    global _current_view, _closing
    if view is None:
        _closing = True
    else:
        _current_view = view
        _closing = False
    logging.getLogger(__name__).debug(f"Current view set to {view.__class__.__name__ if view else None}")

def close_view():
    set_view(None)

_result = None

def set_result(res):
    global _result
    _result = res

def pop_result() -> typing.Optional[typing.Any]:
    global _result
    result = _result
    _result = None
    return result

def close_view_with_result(res):
    set_result(res)
    close_view()

async def _update_async(delta):
    if current_view() is None:
        return
    current_view().update(delta)
    pygame.display.update()
    for event in pygame.event.get():
        current_view().handle_event(event)
    await current_view().do_async()

    global _current_view, _closing
    if _closing:
        _current_view = None
        _closing = False

def _update(delta):
    if current_view() is None:
        return
    current_view().update(delta)
    pygame.display.update()
    for event in pygame.event.get():
        current_view().handle_event(event)

    global _current_view, _closing
    if _closing:
        _current_view = None
        _closing = False

loop = asyncio.get_event_loop()
future = loop.create_future()


async def run_async(view: PyGameView, fps=DEFAULT_FPS) -> typing.Optional[typing.Any]:
    if current_view():
        raise Exception("Cannot run multiple PyGame views at the same time. Currently running: " + current_view_name())
    set_view(view)
    clock = AsyncClock()
    while current_view():
        delta = await clock.tick(fps)
        await _update_async(delta)
    return pop_result()

def run(view: PyGameView, fps=DEFAULT_FPS) -> typing.Optional[typing.Any]:
    if current_view():
        raise Exception("Cannot run multiple PyGame views at the same time. Currently running: " + current_view_name())
    set_view(view)
    clock = pygame.time.Clock()
    while current_view():
        delta = clock.tick(fps) / 1000.0
        _update(delta)
    return pop_result()

async def wait_closed():
    while current_view() is not None:
        await asyncio.sleep(0)

