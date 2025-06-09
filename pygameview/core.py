import pygame
import sys
import logging
import asyncio
import typing

import time
import atexit
count = {}
probes = {}
average_probe_length = 100
average = {}
fps = 60
frame_time = 1/fps
spike_def = 2
critical_def = 4
test_start = None
def log_how_much_time_of_frame(before, what):
    took = time.perf_counter() - before
    if not what in average:
        if what not in count:
            count[what] = 0
            probes[what] = []
        if count[what] < average_probe_length:
            count[what] += 1
            probes[what].append(took)
        if count[what] == average_probe_length:
            probe = probes[what]
            average[what] = sum(probe) / len(probe)
            global test_start
            if not test_start:
                test_start = time.perf_counter()
    elif took/frame_time > 1.0:
        logging.getLogger(__package__).error(f"{what} spiked {took/average[what]:.2f} more than usual. Which is {took/frame_time:.2f} of frame.")
    elif took > average[what]*critical_def:
        logging.getLogger(__package__).warning(f"{what} spiked {took/average[what]:.2f} more than usual. Which is {took/frame_time:.2f} of frame.")
    elif took > average[what]*spike_def:
        logging.getLogger(__package__).info(f"{what} spiked {took/average[what]:.2f} more than usual. Which is {took/frame_time:.2f} of frame.")
    print(f"\r{time.perf_counter() - test_start if test_start else 0:.2f} s", end="")
    return time.perf_counter()

@atexit.register
def log_averages(view = None):
    global test_start
    if test_start:
        view_name = view.__class__.__name__ if view else current_view_name()
        message = f"END OF VIEW {view_name}:\n--- Averages ---"
        for what, av in average.items():
            message += f"\n{what}: {av/frame_time:.2f} of frame"
        message += "\n--- Minimums ---"
        for what, probe in probes.items():
            message += f"\n{what}: {min(probe)/frame_time:.2f} of frame"
        message += "\n--- Test references ---"
        message += f"\nFps: {fps}"
        message += f"\nAverage probe length: {average_probe_length}"
        message += f"\nTest duration: {time.perf_counter() - test_start:.2f} s"
        message += f"\nSpike criteria: {spike_def} times more than average"
        logging.getLogger(__package__).warning(message)
    average.clear()
    count.clear()
    probes.clear()
    test_start = None

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
        # more_than_expected = (awaited*1000/ to_await)
        # if more_than_expected > 2:
        #     tasks = len(asyncio.all_tasks())
        #     logging.getLogger(__package__).info(f"Clock's tick is {more_than_expected} times longer than expected. Tasks: {tasks}. Delay: {delay}.")
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

loop = asyncio.get_event_loop()
future = loop.create_future()


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
        # log_avepyrages(view)
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

