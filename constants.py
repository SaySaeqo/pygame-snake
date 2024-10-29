
class Color:
    red = (255, 0, 0)
    black = (0, 0, 0)
    green = (0, 255, 0)
    white = (255, 255, 255)
    yellowish = (180, 15, 198)
    blue = (0, 0, 255)
    cyan = (0, 255, 255)
    magenta = (255, 0, 255)
    gold = (255, 215, 0)

    default = yellowish

def get_color(idx: int) -> tuple:
    colors = [Color.white, Color.red, Color.green, Color.blue, Color.cyan, Color.magenta, Color.gold]
    return colors[idx % len(colors)]