import pygame
import math
from . import core
from .utils import *

MENU_LINE_SPACING = 30
def titleMenuDrawer(title: str):
    return MenuDrawer(MENU_LINE_SPACING)\
        .draw(title, 72)\
        .add_space(MENU_LINE_SPACING)

class ScrollableView(core.PyGameView):
        
        SCROLL_SPEED = 10
    
        def __init__(self, title: str, scrollable: str):
            self.title = title
            self.scrollable = text2surface(scrollable)
            self.scroll = 0
            self.visible_height = pygame.display.get_surface().get_height() - 3*MENU_LINE_SPACING - text2surface(title, 72).get_height()
    
        def update(self, delta):
            titleMenuDrawer(self.title)\
                .draw_surface(self.scrollable.subsurface(pygame.Rect(
                        0, self.scroll*self.SCROLL_SPEED,
                        self.scrollable.get_width(), min(self.visible_height, self.scrollable.get_height())
                    )))
            
            keys = pygame.key.get_pressed()
            if keys[pygame.K_DOWN]:
                self.scroll = min(self.scroll + 1, (self.scrollable.get_height()-self.visible_height)//self.SCROLL_SPEED)
            if keys[pygame.K_UP]:
                self.scroll = max(0, self.scroll - 1)

        def handle_event(self, event):
            super().handle_event(event)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    core.close_view()

class InputView(core.PyGameView):
    """
    View with text input. There are no side effects. Max length of input is 24 chars.
    Controls:
    - Esc -> return None
    - Enter -> return string
    - Del -> clear a string
    - Backspace -> deletes last char
    """

    MAX_INPUT_LENGTH = 24
    
    def __init__(self, title: str, value: str, character_filter=lambda c: True):
        self.title = title
        self.value = value
        self.character_filter = character_filter

    def update(self, delta):
        titleMenuDrawer(self.title)\
            .draw(self.value)

    def handle_event(self, event):
        super().handle_event(event)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                core.close_view_with_result(self.value)
            elif event.key == pygame.K_ESCAPE:
                core.close_view()
            elif event.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]
            elif event.key == pygame.K_DELETE:
                self.value = ""
            elif len(self.value) < self.MAX_INPUT_LENGTH \
                    and event.unicode.isprintable()\
                    and self.character_filter(event.unicode):
                self.value += event.unicode

class KeyInputView(core.PyGameView):
    
    def __init__(self, title: str):
        self.title = title

    def update(self, delta):
        titleMenuDrawer(self.title)

    def handle_event(self, event):
        super().handle_event(event)
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                core.close_view()
            else:
                core.close_view_with_result(event.key)

class MenuView(core.PyGameView):
        
        OPTION_OFFSET = 10
        OUTLINE_WIDTH = 2
    
        def __init__(self, title: str, options: list, choice=0):
            self.title = title
            self.options = options
            self.choice = choice
    
        def update(self, delta):
            drawer = titleMenuDrawer(self.title)
            for idx, option in enumerate(self.options):
                if idx == self.choice:
                    selected = get_with_outline(text2surface(option), self.OUTLINE_WIDTH)
                    drawer.add_space(-self.OUTLINE_WIDTH).draw_surface(selected).add_space(self.OPTION_OFFSET-self.OUTLINE_WIDTH)
                else:
                    drawer.draw(option).add_space(self.OPTION_OFFSET)
            
        def handle_event(self, event):
            super().handle_event(event)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.choice = (self.choice - 1) % len(self.options)
                elif event.key == pygame.K_DOWN:
                    self.choice = (self.choice + 1) % len(self.options)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    core.close_view_with_result(self.choice)
                elif event.key == pygame.K_ESCAPE:
                    core.close_view()

async def show_menu(title, menu):
    """
    menu should be function returning tuple of 2 lists:
    - list of options names
    - list of options' couritines to be awaited when chosen
    """
    choice = 0
    while True:
        options, methods = menu()
        choice = await MenuView(title, options, choice)
        if choice == None: break
        await methods[choice]()

class WaitingView(core.PyGameView):
    
    def __init__(self, msg: str):
        self.msg = msg
        self.count = 0.0

    def update(self, delta):
        title(self.msg + "."*math.floor(self.count), Align.CENTER)
        self.count = (self.count + delta) % 4

    def handle_event(self, event):
        super().handle_event(event)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
            core.close_view()