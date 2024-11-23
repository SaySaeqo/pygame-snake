import pygame
import sys
from constants import Color
from utils import unique
from screeninfo import get_monitors
import apygame
from math import floor
import MyPodSixNet as net

WINDOWS_FUNCTIONS_FPS = 10

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

        
def await_keypress(check_key, check_keys=lambda keys: False, clock=pygame.time.Clock()):
    pygame.display.update()
    while True:
        clock.tick(WINDOWS_FUNCTIONS_FPS)
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and check_key(event.key): 
                return
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                sys.exit()
        if check_keys(pygame.key.get_pressed()): 
            return

def pause(message="PAUSED"):
    title(message, Align.CENTER)
    await_keypress(lambda key: key in (pygame.K_p, pygame.K_PAUSE, pygame.K_SPACE, pygame.K_ESCAPE, pygame.K_RETURN))

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
        try:
            next_resolution = RESOLUTIONS[RESOLUTIONS.index(current_resolution)+1]
        except (IndexError, ValueError) as e:
            next_resolution = RESOLUTIONS[0]
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

def menu(title, options, choice=0):

    if not options:
        raise ValueError("Options list cannot be empty")
    
    while True:

        pygame.display.get_surface().fill(Color.black)

        TITLE_OFFSET = 30
        offset = TITLE_OFFSET
        title_sur = text2surface(title, 72)
        merge_into_board(title_sur, Align.TOP, offset)

        offset += title_sur.get_height() + TITLE_OFFSET

        OPTION_OFFSET = 10
        for idx, option in enumerate(options):
            option_sur = text2surface(option)
            if idx == choice:
                OUTLINE_WIDTH = 2
                option_sur = get_with_outline(option_sur, OUTLINE_WIDTH)
                offset -= OUTLINE_WIDTH
            merge_into_board(option_sur, Align.TOP, offset)
            offset += option_sur.get_height() + OPTION_OFFSET
            if idx == choice:
                offset -= OUTLINE_WIDTH

        enter = False
        def operate(key):
            nonlocal choice
            nonlocal enter
            if key == pygame.K_UP:
                choice = (choice - 1) % len(options)
            elif key == pygame.K_DOWN:
                choice = (choice + 1) % len(options)
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                enter = True
            else:
                return False
            return True
            
        await_keypress(operate)

        if (enter):
            return choice, options[choice]
        

def inputbox(title, default="", character_filter=lambda ch: True):
    TITLE_OFFSET = 30
    pygame.display.get_surface().fill(Color.black)
    title_sur = text2surface(title, 72)
    merge_into_board(title_sur, Align.TOP, TITLE_OFFSET)

    offset = TITLE_OFFSET + title_sur.get_height() + TITLE_OFFSET

    input_text = default
    while True:
        input_sur = text2surface(input_text)
        background = pygame.Surface((pygame.display.get_surface().get_rect().width, input_sur.get_height()))
        merge_into_board(background, Align.TOP, offset)
        merge_into_board(input_sur, Align.TOP, offset)

        enter = False
        def operate(key):
            nonlocal input_text
            nonlocal enter
            if key == pygame.K_BACKSPACE and input_text:
                input_text = input_text[:-1]
            elif key == pygame.K_RETURN:
                enter = True
            elif key == pygame.K_DELETE:
                input_text = ""
            else:
                try:
                    key = chr(key)
                    if not key.isprintable(): return False
                    if not character_filter(key): return False
                    input_text += key
                except ValueError as e:
                    return False
            return True

        await_keypress(operate)

        if enter:
            return input_text

def keyinputbox(title):
    TITLE_OFFSET = 30
    pygame.display.get_surface().fill(Color.black)
    title_sur = text2surface(title, 72)
    merge_into_board(title_sur, Align.TOP, TITLE_OFFSET)

    chosen_key = None

    def operate(key):
        nonlocal chosen_key
        if key != pygame.K_RETURN:
            chosen_key = key
        return True

    await_keypress(operate)
    return chosen_key

def read_leaderboard_file(filepath, sort_key=lambda line: int(line.split(": ")[1]), name_key=lambda line: line.split(": ")[0], max_results=50):
    try:
        lines = []
        with open(filepath, "r+") as file:
            lines = file.readlines()

            lines = sorted(lines, key=sort_key, reverse=True)
            lines = unique(lines, key=name_key)
            lines = lines[:max_results]

            file.seek(0)
            file.writelines(lines)
            file.truncate()

            return "".join(lines) or "Empty"

    except FileNotFoundError as e:
        return "Empty"


async def network_room(players, host):
    clock = apygame.Clock()
    while True:

        players_phrase = ""
        for player in players:
            players_phrase += f"{player})\n"
        
        SOME_OFFSET = 30
        MenuDrawer(SOME_OFFSET)\
            .draw("Network Room", 72)\
            .draw("(Press enter to start)", 18)\
            .add_space(SOME_OFFSET)\
            .draw(f"Host: {host}", 24)\
            .add_space(SOME_OFFSET*2)\
            .draw(players_phrase)

        pygame.display.update()
        net.send("lobby", players)

        await clock.tick(WINDOWS_FUNCTIONS_FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                return True
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False
            
async def wait_screen(msg):
    clock = apygame.Clock()
    count = 0
    frame_time = 1/WINDOWS_FUNCTIONS_FPS
    while True:
        pygame.display.get_surface().fill(Color.black)
        title(f"{msg}{'.'*floor(count)}", Align.CENTER)
        count = (count + frame_time) % 4
        pygame.display.update()
        await clock.tick(WINDOWS_FUNCTIONS_FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                return