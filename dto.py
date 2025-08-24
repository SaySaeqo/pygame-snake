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
    
import struct

pygameutils.create_window("test")

test = GameState()
test.init(2)

dict_data = test.to_json()
print(dict_data)

def serialize(v):
    if isinstance(v, int):
        return struct.pack("i", v)
    if isinstance(v, float):
        return struct.pack("f", v)
    if isinstance(v, bool):
        return struct.pack("?", v)
    if isinstance(v, str):
        encoded = v.encode('utf-8')
        return encoded + b"\x00"
    if isinstance(v, list) or isinstance(v, tuple):
        result = struct.pack("I", len(v))
        for item in v:
            result += serialize(item)
        return result
    if isinstance(v, dict):
        result = b""
        for value in v.values():
            result += serialize(value)
        return result
    raise ValueError(f"Cannot serialize type {type(v)}")

def get_serialized_size(v, s):
    if isinstance(v, int):
        return struct.calcsize("i")
    if isinstance(v, float):
        return struct.calcsize("f")
    if isinstance(v, bool):
        return struct.calcsize("?")
    if isinstance(v, dict):
        serialized_sizes = []
        for value in v.values():
            size = get_serialized_size(value, s)
            serialized_sizes.append(size)
            s = s[size:]
        return sum(serialized_sizes)
    if isinstance(v, list) or isinstance(v, tuple):
        return struct.unpack("I", s[:4])[0] * get_serialized_size(v[0], s[4:]) + 4 if len(v) > 0 else 4
    if isinstance(v, str):
        return utils.find_index(s, b"\x00") + 1
    raise ValueError(f"Cannot get size for type {type(v)}")

def deserialize(data, data_type, s, v):
    if data_type == int:
        return struct.unpack("i", data)[0]
    if data_type == float:
        return struct.unpack("f", data)[0]
    if data_type == bool:
        return struct.unpack("?", data)[0]
    if data_type == str:
        return data.decode('utf-8')[:-1]
    if data_type == list or data_type == tuple:
        deserialized_list = []
        length = struct.unpack("I", s[:4])[0]
        s = s[4:]
        if len(v) == 0:
            if length == 0:
                return deserialized_list
            else:
                raise ValueError("Cannot determine item type for empty list")
        items_type = type(v[0])
        for _ in range(length):
            item = deserialize(s[:get_serialized_size(v[0], s)], items_type, s, v[0])
            s = s[get_serialized_size(v[0], s):]
            deserialized_list.append(item)
        return deserialized_list
    if data_type == dict:
        deserialized_dict = {}
        for key, value in v.items():
            deserialized_dict[key] = deserialize(s[:get_serialized_size(value, s)], type(value), s, value)
            s = s[get_serialized_size(value, s):]
        return deserialized_dict
    raise ValueError(f"Cannot deserialize type {data_type}")

serialized = serialize(dict_data)
print(serialized)

result = {}
for k, v in dict_data.items():
    result[k] = deserialize(serialized[:get_serialized_size(v, serialized)], type(v), serialized, v)
    serialized = serialized[get_serialized_size(v, serialized):]
