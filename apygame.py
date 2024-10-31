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
 
        end_time = (1.0 / fps) * 1000
        current = self.time_func()
        time_diff = current - self.last_tick
        delay = (end_time - time_diff) / 1000
 
        self.last_tick = current
        if delay < 0:
            delay = 0
 
        await asyncio.sleep(delay)

class PyGameView:

    def update(self):
        pass

    def handle_event(self, event):
        if (event.type == pygame.QUIT):
            sys.exit()

    async def async_operation(self):
        pass
        


@singleton
class CurrentPyGameView:

    _view = PyGameView()

    async def update(self):
        self._view.update()
        pygame.display.flip()
        for event in pygame.event.get():
            self._view.handle_event(event)
        await self._view.async_operation()

    def set(self, value: PyGameView):
        if (not isinstance(value, PyGameView)):
            raise TypeError("value must be a PyGameView")
        if not value:
            raise ValueError("value must not be None")
        self._view = value


async def init(fps=60):
    """
    To be used once after creating pygame window.
    """
    clock = Clock()
    while True:
        await CurrentPyGameView().update()
        await clock.tick(fps)

def setView(view: PyGameView):
    CurrentPyGameView().set(view)
    logging.getLogger(__name__).debug(f"Current view set to {view.__class__.__name__}")

