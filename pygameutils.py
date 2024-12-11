import pygame
import screeninfo
import math
import pygameview
import constants


def get_screen_size() -> tuple[int, int]:
    monitor = screeninfo.get_monitors()[0]
    return monitor.width, monitor.height

def next_screen_resolution():
    RESOLUTIONS = [(800, 600), (1024, 768), (1280, 720), (1600, 900), (1920, 1080), get_screen_size()]

    if not (pygame.get_init and pygame.display.get_surface()):
        pygame.display.set_mode(RESOLUTIONS[0], pygame.FULLSCREEN if RESOLUTIONS[0] == get_screen_size() else 0)
        pygameview.utils.set_font_scale(constants.TEXT_LINES_PER_SCREEN)
        return

    current_resolution = pygame.display.get_window_size()
    if current_resolution == get_screen_size():
        next_resolution = RESOLUTIONS[0]
    else:
        next_resolution = RESOLUTIONS[RESOLUTIONS.index(current_resolution)+1]
    pygame.display.set_mode(next_resolution, pygame.FULLSCREEN if next_resolution == get_screen_size() else 0)
    pygameview.utils.set_font_scale(constants.TEXT_LINES_PER_SCREEN)

def create_window(title, width=None, height=None, icon=None):
    if pygame.get_init() and pygame.display.get_surface(): return
    pygame.init()
    pygame.display.set_caption(title)
    if icon:
        pygame.display.set_icon(icon)
    if width and height:
        full_screen = get_screen_size() == (width, height)
        pygame.display.set_mode((width, height), pygame.FULLSCREEN if full_screen else 0)
        pygameview.utils.set_font_scale(constants.TEXT_LINES_PER_SCREEN)
    else:
        next_screen_resolution()

def draw_arrow(surface: pygame.Surface, color, center: pygame.Vector2, direction: pygame.Vector2, width, radius):
    """
    :param width: width of the line
    :param radius: length from the center to tip of the arrow
    """
    pygame.draw.line(surface, color, center - direction * radius, center + direction * radius, width)
    pygame.draw.line(surface, color, center + direction * radius, center + direction * radius - direction.rotate(45) * radius/2, width)
    pygame.draw.line(surface, color, center + direction * radius, center + direction * radius - direction.rotate(-45) * radius/2, width)

def get_surface_corners(surface: pygame.Surface) -> tuple[pygame.Vector2, pygame.Vector2, pygame.Vector2, pygame.Vector2]:
    """
    From top left corner, clockwise
    """
    return (
        pygame.Vector2(0, 0),
        pygame.Vector2(surface.get_width(), 0),
        pygame.Vector2(surface.get_width(), surface.get_height()),
        pygame.Vector2(0, surface.get_height())
    )

def paint_surface(square_surface: pygame.Surface, color, percentage: float, direction: pygame.Vector2) -> pygame.Surface:

    if percentage <= 0:
        return square_surface.copy()
    elif percentage >= 1:
        mask = pygame.mask.from_surface(square_surface)
        return mask.to_surface(square_surface.copy(), setcolor=color, unsetcolor=None)

    # don't ask me why, but this is how angle_to works
    alfa = pygame.Vector2(-1, 0).angle_to(direction) + 45
    alfa = abs(alfa)
    quarter = 1
    while alfa > 45:
        quarter -= 1
        quarter %= 4
        alfa -= 90

    full_len = math.cos(math.radians(alfa)) * square_surface.get_width() * math.sqrt(2)
    len = full_len * percentage

    divider = direction.rotate(90)
    starting_point = get_surface_corners(square_surface)[quarter]
    point_on_divider = starting_point + direction * len
    
    painting_surface = square_surface.copy()
    pygame.draw.polygon(painting_surface, color, [
        point_on_divider + divider * square_surface.get_width()*2,
        point_on_divider - divider * square_surface.get_width()*2,
        starting_point - divider * square_surface.get_width()*2,
        starting_point + divider * square_surface.get_width()*2
    ])

    mask = pygame.mask.from_surface(square_surface)
    return mask.to_surface(square_surface.copy(), painting_surface, unsetcolor=None)