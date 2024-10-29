import pygame
from singleton_decorator import singleton
from asyncclock import Clock
import sys
import windowfunctions
import snake_utils

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


async def run_pygame_async(fps=60):
    """
    To be used once after creating pygame window.
    """
    clock = Clock()
    while True:
        await CurrentPyGameView().update()
        await clock.tick(fps)

def setView(view: PyGameView):
    CurrentPyGameView().set(view)
    snake_utils.log().info(f"Set view to {view.__class__.__name__}")

