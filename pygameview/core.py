import pygame
from singleton_decorator import singleton
import sys
import logging
import asyncio
import constants

class AsyncClock:
    def __init__(self, time_func=pygame.time.get_ticks):
        self.time_func = time_func
        self.last_tick = time_func() or 0
 
    async def tick(self, fps=0):
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

@singleton
class CurrentPyGameView:

    view = PyGameView()
    result = None

    async def update_async(self, delta):
        if self.view is None:
            return
        self.view.update(delta)
        pygame.display.flip()
        for event in pygame.event.get():
            self.view.handle_event(event)
        await self.view.do_async()
        if self.closing:
            self.view = None
            self.closing = False

    def update(self, delta):
        if self.view is None:
            return
        self.view.update(delta)
        pygame.display.flip()
        for event in pygame.event.get():
            self.view.handle_event(event)
        if self.closing:
            self.view = None
            self.closing = False

    def set(self, view):
        if view is None:
            self.closing = True
        else:
            self.view = view
            self.closing = False

    def popResult(self):
        result = self.result
        self.result = None
        return result

# just to make sure that only one view is running at the same time
_mutex = False
def _grab_mutex():
    global _mutex
    if _mutex:
        raise Exception("Cannot run multiple PyGame views at the same time. Currently running: " + CurrentPyGameView().view.__class__.__name__)
    _mutex = True
def _release_mutex():
    global _mutex
    _mutex = False
############################

async def run_async(view: PyGameView, fps=constants.Game.fps):
    try:
        _grab_mutex()
        set_view(view)
        clock = AsyncClock()
        while CurrentPyGameView().view:
            delta = await clock.tick(fps)
            await CurrentPyGameView().update_async(delta)
        result = CurrentPyGameView().popResult()
        return result
    finally:
        _release_mutex()

def run(view: PyGameView, fps=constants.Game.fps):
    try:
        _grab_mutex()
        set_view(view)
        clock = pygame.time.Clock()
        while CurrentPyGameView().view:
            delta = clock.tick(fps) / 1000.0
            CurrentPyGameView().update(delta)
        result = CurrentPyGameView().popResult()
        return result
    finally:
        _release_mutex()

def set_view(view: PyGameView):
    CurrentPyGameView().set(view)
    logging.getLogger(__name__).debug(f"Current view set to {view.__class__.__name__}")

def close_view():
    set_view(None)

def close_view_with_result(result):
    CurrentPyGameView().result = result
    close_view()

async def wait_closed():
    while _mutex:
        await asyncio.sleep(0)

