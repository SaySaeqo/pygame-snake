import logging

class Color:
    black = (0, 0, 0)
    white = (255, 255, 255)
    red = (255, 0, 0)
    yellowish = (180, 15, 198)
    blue = (0, 0, 255)

    green = (0, 255, 0)
    cyan = (0, 255, 255)
    magenta = (255, 0, 255)
    gold = (255, 215, 0)

    default = yellowish
    
    @staticmethod
    def values():
        return (getattr(Color, attr) for attr in vars(Color) if not callable(getattr(Color, attr)) and not attr.startswith("__"))
    
    @staticmethod
    def players_colors():
        return (c for c in Color.values() if not c in (Color.black, Color.green, Color.cyan, Color.gold, Color.magenta))
    
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

LOG = logging.getLogger("snake")