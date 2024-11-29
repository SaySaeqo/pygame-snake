import pygame
import screeninfo


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