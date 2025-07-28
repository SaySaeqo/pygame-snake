# You can try to import profiling_helpers if you want some manual profiling here...

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

        # For debugging and profiling purposes
        # more_than_expected = (awaited*1000/ to_await)
        # if more_than_expected > 2:
        #     tasks = len(asyncio.all_tasks())
        #     logging.getLogger(__package__).debug(f"Clock's tick is {more_than_expected} times longer than expected. Tasks: {tasks}. Delay: {delay}.")
        
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
    if view is _current_view:
        return
    if view is None:
        _closing = True
    else:
        _current_view = view
        _closing = False
    logging.getLogger(__package__).debug(f"Current view set to {view.__class__.__name__ if view else None}")

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
    # before = time.perf_counter()
    current_view().update(delta)
    # before = log_how_much_time_of_frame(before, "Update")
    pygame.display.update()
    # before = log_how_much_time_of_frame(before, "Update display")
    for event in pygame.event.get():
        current_view().handle_event(event)
    # before = log_how_much_time_of_frame(before, "Handle event")
    await current_view().do_async()
    # before = log_how_much_time_of_frame(before, "Do async")

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


async def run_async(view: PyGameView, fps=DEFAULT_FPS) -> typing.Optional[typing.Any]:
    try:
        if _closing:
            await wait_closed()
        if current_view():
            raise Exception("Cannot run multiple PyGame views at the same time. Currently running: " + current_view_name())
        set_view(view)
        clock = AsyncClock()
        while current_view():
            delta = await clock.tick(fps)
            await _update_async(delta)
        # log_averages(view)
        return pop_result()
    finally:
        global _current_view
        _current_view = None

def run(view: PyGameView, fps=DEFAULT_FPS) -> typing.Optional[typing.Any]:
    try:
        if current_view():
            raise Exception("Cannot run multiple PyGame views at the same time. Currently running: " + current_view_name())
        set_view(view)
        clock = pygame.time.Clock()
        while current_view():
            delta = clock.tick(fps) / 1000.0
            _update(delta)
        return pop_result()
    finally:    
        global _current_view
        _current_view = None

async def wait_closed():
    while current_view():
        await asyncio.sleep(0)

