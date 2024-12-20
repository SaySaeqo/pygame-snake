import logging
import utils
import enum

class Color:
    black = (0, 0, 0)
    white = (255, 255, 255)
    red = (255, 0, 0)
    yellowish = (180, 198, 15)
    blue = (0, 0, 255)

    green = (0, 255, 0)
    cyan = (0, 255, 255)
    magenta = (255, 0, 255)
    gold = (255, 215, 0)
    gray = (128, 128, 128)

    # Additional colors
    orange = (255, 165, 0)
    purple = (128, 0, 128)
    pink = (255, 192, 203)
    brown = (165, 42, 42)
    navy = (0, 0, 128)
    lime = (0, 255, 0)
    teal = (0, 128, 128)
    olive = (128, 128, 0)
    maroon = (128, 0, 0)

    default = yellowish
    
    @staticmethod
    def values():
        return (getattr(Color, attr) for attr in vars(Color) if not callable(getattr(Color, attr)) and not attr.startswith("__"))
    
    @staticmethod
    def players_colors():
        return (c for c in Color.values() if not c in (Color.black, Color.green, Color.cyan, Color.gold, Color.magenta))
    
@utils.singleton
class Game:
    """
    :param diameter: size of things in pixels
    :param speed: diameters per second
    :param time_limit: seconds
    """
    diameter  = 30
    speed  = 4
    time_limit = 60
    rotation_power = 4
    screen_rect = None

LOG = logging.getLogger("snake")

DEFAULT_PORT = 52413

TEXT_LINES_PER_SCREEN = 18

WINDOW_TITLE = "Snake v1.0+"

class Powerup(enum.Enum):
    NONE = Color.green
    WEIRD_WALKING = Color.magenta
    WALL_WALKING = Color.cyan
    CRUSHING = Color.gold
    GHOSTING = Color.gray

POWERUP_TIMES = {
    Powerup.WALL_WALKING: 5.0,
    Powerup.WEIRD_WALKING: 10.0,
    Powerup.CRUSHING: 10.0,
    Powerup.GHOSTING: 5.0
}