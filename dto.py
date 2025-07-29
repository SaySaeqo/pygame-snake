from dataclasses import dataclass, field, asdict
from constants import *
from decisionfunctions import based_on_keys
from gameobjects import *
import utils
import pygameutils
import toolz
import constants
import time

@dataclass
class Control:
    left: int
    right: int 

@utils.singleton
class Config:
    names = ["snake", "snake2", "snake3"]
    number_of_players = 1
    controls = [Control(pygame.K_LEFT, pygame.K_RIGHT), Control(pygame.K_a, pygame.K_d), Control(pygame.K_j, pygame.K_l)]
    last_connected_ip = "localhost"
    FILE_NAME = "config.data"

    @property
    def active_players_names(self):
        return self.names[:self.number_of_players]

    @property
    def control_functions(self):
        return [based_on_keys(control.left, control.right) for control in self.controls]

    def save_to_file(self):
        with open(self.FILE_NAME, "w") as file:
            for idx, name in enumerate(self.names):
                file.write(f"player {idx+1} name: {name}\n")
            for control in self.controls:
                file.write(f"player {self.controls.index(control)+1} controls: {pygame.key.name(control.left)} {pygame.key.name(control.right)}\n")
            file.write(f"resolution: {pygame.display.get_window_size()[0]} {pygame.display.get_window_size()[1]}\n")
            file.write(f"last_connected_ip: {self.last_connected_ip}\n")

    def load_from_file(self):
        try:
            with open(self.FILE_NAME, "r") as file:
                for line in file:
                    if line.startswith("player"):
                        pygame.init()
                        parts = line.split()
                        player = int(parts[1]) - 1
                        if (parts[2] == "name:"):
                            self.names[player] = " ".join(parts[3:])
                        if (parts[2] == "controls:"):
                            self.controls[player].left = pygame.key.key_code(parts[3])
                            self.controls[player].right = pygame.key.key_code(parts[4])
                    if line.startswith("resolution"):
                        key, w, h = line.split()
                        w = int(w)
                        h = int(h)
                        full_screen = pygameutils.get_screen_size()
                        if full_screen[0] < w or full_screen[1] < h:
                            w, h = full_screen
                        pygameutils.create_window(constants.WINDOW_TITLE, w, h)
                    if line.startswith("last_connected_ip"):
                        parts = line.split()
                        self.last_connected_ip = parts[1]
        except FileNotFoundError:
            ...

def default_name_key(line):
    return line.split(" ")[0] + " ".join(line.split(" ")[2:])

def read_leaderboard_file(filepath, sort_key=lambda line: int(line.split(" ")[1]), name_key=default_name_key, max_results=50):
    try:
        lines = []
        with open(filepath, "r+") as file:
            lines = file.readlines()

            lines = sorted(lines, key=sort_key, reverse=True)
            lines = toolz.unique(lines, key=name_key)
            lines = list(toolz.take(max_results, lines))

            file.seek(0)
            file.writelines(lines)
            file.truncate()

            return "".join(lines) or "Empty"

    except FileNotFoundError as e:
        return "Empty"

@dataclass
class GameState:
    players: list[Snake] = field(default_factory=list)
    fruits: list[Fruit] = field(default_factory=list)
    walls: list[Wall] = field(default_factory=list)
    time_passed: float = 0
    fruit_event_timer: float = 0
    wall_event_timer: float = 0
    wall_walking_event_timer: float = 0
    current_speed: int = 0
    scores: list[int] = field(default_factory=list)
    timestamp: float = time.time()
    last_delta: float = 0.0
    numbering: int = 0

    def init(self, number_of_players):
        radius = Game().diameter / 2
        color = Color.players_colors()
        for _ in range(number_of_players):
            player = Snake.at_random_position(radius, next(color))
            self.players.append(player)
        self.fruits=[Fruit.at_random_position(radius) for _ in range(6)]
        self.current_speed= Game().speed
        self.scores=[0] * number_of_players

    def get_init(self):
        return len(self.players) > 0

    def alive_players(self):
        return filter(lambda x: x.alive, self.players)
    
    def enumerate_alive_players(self):
        for idx, player in enumerate(self.players):
            if player.alive:
                yield idx, player

    def all_players_dead(self):
        return all(not player.alive for player in self.players)

    def copy_values(self, other):
        if not isinstance(other, dict):
            other = asdict(other)
        for k, v in other.items():
            setattr(self, k, v)

    def reset(self):
        self.copy_values(GameState())

    def to_json(self):
        res = asdict(self)
        for k, v in res.items():
            if isinstance(v, list) and len(v) > 0 and hasattr(v[0], "to_json"):
                res[k] = [item.to_json() for item in v]
        return res
    
    @classmethod
    def from_json(cls, data):
        res = cls()
        res.copy_values(data)
        res.players = [Snake.from_json(player) for player in data["players"]]
        res.fruits = [Fruit.from_json(fruit) for fruit in data["fruits"]]
        res.walls = [Wall.from_json(wall) for wall in data["walls"]]
        return res
    