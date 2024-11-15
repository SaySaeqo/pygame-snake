import pygame
from singleton_decorator import singleton
import sys
import logging
import asyncio

class Clock:
    def __init__(self, time_func=pygame.time.get_ticks):
        self.time_func = time_func
        self.last_tick = time_func() or 0
 
    async def tick(self, fps=0):
        if 0 >= fps:
            return
 
        to_await = (1.0 / fps) * 1000
        now = self.time_func()
        since_last_tick = now - self.last_tick
        delay = (to_await - since_last_tick) / 1000
        self.last_tick = now

        await asyncio.sleep(delay)

class PyGameView:

    def update(self, delta):
        pass

    def handle_event(self, event):
        if (event.type == pygame.QUIT):
            sys.exit()

    async def async_operation(self):
        pass
        


@singleton
class CurrentPyGameView:

    view = PyGameView()
    result = None

    async def update(self, delta):
        if self.view is None:
            return
        self.view.update(delta)
        pygame.display.flip()
        for event in pygame.event.get():
            self.view.handle_event(event)
        await self.view.async_operation()
        if self.closing:
            self.view = None
            self.closing = False

    def set(self, view):
        if view is None:
            self.closing = True
        else:
            self.view = view
            self.closing = False


async def init(fps=60):
    """
    To be used once after creating pygame window.
    """
    clock = Clock()
    delta = 1 / fps
    while CurrentPyGameView().view:
        await CurrentPyGameView().update(delta)
        await clock.tick(fps)

def setView(view: PyGameView):
    CurrentPyGameView().set(view)
    logging.getLogger(__name__).debug(f"Current view set to {view.__class__.__name__}")