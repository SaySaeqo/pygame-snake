import pygame
import screeninfo
import math


def get_screen_size():
    monitor = screeninfo.get_monitors()[0]
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

def paint_surface(square_surface: pygame.Surface, color, percentage: int, direction: pygame.Vector2) -> pygame.Surface:

    alfa = pygame.Vector2(1, 1).angle_to(direction)
    quarter = 1
    while alfa > 45:
        quarter += 1
        alfa -= 90

    full_len = math.cos(math.radians(alfa)) * square_surface.get_width() * math.sqrt(2)
    len = full_len * percentage / 100

    divider = direction.rotate(90)
    point_on_divider = direction * len
    starting_point = pygame.Vector2(0 if quarter in (1,4) else 1, 0 if quarter in (1,2) else 1) * square_surface.get_width()
    
    painting_surface = square_surface.copy()
    pygame.draw.polygon(painting_surface, color, [
        point_on_divider + divider * square_surface.get_width(),
        point_on_divider - divider * square_surface.get_width(),
        starting_point - divider * square_surface.get_width(),
        starting_point + divider * square_surface.get_width()
    ])

    mask = pygame.mask.from_surface(square_surface)

    return mask.to_surface(square_surface.copy(), painting_surface, unsetcolor=None)


    