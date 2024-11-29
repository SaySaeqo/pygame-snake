import sys
import pygame
from screeninfo import get_monitors

class Color:
    white = (255, 255, 255)
    black = (0, 0, 0)

class Align:
    CENTER = 0
    TOP = 1
    BOTTOM = 2

def text2surface(text: str, font_size=32, with_background=False) -> pygame.Surface:
    LINE_SPACING = 10  # distance between lines for displayed text (in pixels)
    FONT = pygame.font.SysFont("monospace", font_size, bold=True)


    # chopping line of text into separate surfaces
    lines = (t for t in text.split("\n"))
    text_surfaces = [FONT.render(line, True, Color.white) for line in lines]

    # combining into 1 surface (align: horizontally centered)
    main_surface = pygame.Surface((
        max(t.get_rect().width for t in text_surfaces),
        sum(t.get_rect().height for t in text_surfaces) + LINE_SPACING * (len(text_surfaces)-1)
    ), flags=0 if with_background else pygame.SRCALPHA)
    y = 0
    for sur in text_surfaces:
        main_surface.blit(sur, (main_surface.get_rect().centerx - sur.get_rect().centerx, y))
        y += sur.get_height() + LINE_SPACING

    return main_surface

def merge_into_board(surface: pygame.Surface, align=Align.TOP, offset=0):
    """ 
    :param align: horizontally always centered; vertically as desired)
    """
    x = pygame.display.get_surface().get_rect().centerx - surface.get_rect().centerx
    if align == Align.TOP:
        y = offset
    elif align == Align.CENTER:
        y = pygame.display.get_surface().get_rect().centery - surface.get_rect().centery
    elif align == Align.BOTTOM:
        y = pygame.display.get_surface().get_height() - surface.get_height() - offset
    else:
        raise RuntimeError("Align parameter is not correct")
    pygame.display.get_surface().blit(surface, (x, y))

def title(text: str, align=Align.TOP, font_size=32, offset=0):
    """
    Merge of functions: text2surface, merge_into_board
    """

    if not text: return
    surface = text2surface(text, font_size)
    merge_into_board(surface, align, offset)

class MenuDrawer:

    def __init__(self, initial_offset=0):
        self.offset = initial_offset
        pygame.display.get_surface().fill(Color.black)

    def draw(self, text: str, font_size=32, align=Align.TOP):
        surface = text2surface(text, font_size)
        return self.draw_surface(surface, align)
    
    def draw_surface(self, surface: pygame.Surface, align=Align.TOP):
        merge_into_board(surface, align, self.offset)
        self.offset += surface.get_height()
        return self

    def add_space(self, offset):
        self.offset += offset
        return self

def get_screen_size():
    monitor = get_monitors()[0]
    return monitor.width, monitor.height

def next_screen_resolution():
    RESOLUTIONS = [(800, 600), (1024, 768), (1280, 720), (1600, 900), (1920, 1080), get_screen_size()]

    if not (pygame.get_init and pygame.display.get_surface()):
        pygame.display.set_mode(RESOLUTIONS[0], pygame.FULLSCREEN if RESOLUTIONS[0] == get_screen_size() else 0)
        return

    current_resolution = pygame.display.get_window_size()
    if current_resolution == get_screen_size():
        next_resolution = RESOLUTIONS[0]
    else:
        next_resolution = RESOLUTIONS[RESOLUTIONS.index(current_resolution)+1]
    pygame.display.set_mode(next_resolution, pygame.FULLSCREEN if next_resolution == get_screen_size() else 0)

def create_window(title, width=None, height=None, icon=None):
    if pygame.get_init() and pygame.display.get_surface(): return
    pygame.init()
    pygame.display.set_caption(title)
    if icon:
        pygame.display.set_icon(icon)
    if width and height:
        full_screen = get_screen_size() == (width, height)
        pygame.display.set_mode((width, height), pygame.FULLSCREEN if full_screen else 0)
    else:
        next_screen_resolution()

def get_with_outline(surface, width=2):
    outline = pygame.Surface((surface.get_width() + width * 2, surface.get_height() + width * 2))
    outline.fill(Color.white)
    inner_surface = surface.copy()
    inner_surface.fill(Color.black)
    outline.blit(inner_surface, (width, width))
    outline.blit(surface, (width, width))
    
    return outline