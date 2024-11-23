from dataclasses import dataclass, field

from constants import *
from gameobjects import *


@dataclass
class Options:
    """
    :param diameter: size of things in pixels
    :param speed: diameters per second
    :param time_limit: seconds
    """
    fps: int = 60
    diameter: int = 30
    speed: int = 4
    time_limit: int = 60
    rotation_power: int = 4
    resolution: tuple[int, int] = (800, 600)

    def to_json(self):
        return {
            "fps": self.fps,
            "diameter": self.diameter,
            "speed": self.speed,
            "time_limit": self.time_limit,
            "rotation_power": self.rotation_power,
            "resolution": self.resolution
        }
    
    @classmethod
    def from_json(cls, data):
        return cls(
            fps=data["fps"],
            diameter=data["diameter"],
            speed=data["speed"],
            time_limit=data["time_limit"],
            rotation_power=data["rotation_power"],
            resolution=data["resolution"]
        )
    
    def copy_values(self, other):
        self.fps = other.fps
        self.diameter = other.diameter
        self.speed = other.speed
        self.time_limit = other.time_limit
        self.rotation_power = other.rotation_power
        self.resolution = other.resolution

@dataclass
class GameState:
    players: list[Snake] = field(default_factory=list)
    fruits: list[Fruit] = field(default_factory=list)
    walls: list[Wall] = field(default_factory=list)
    time_passed: float = 0
    fruit_event_timer: float = 0
    wall_event_timer: float = 0
    wall_walking_event_timer: float = 0
    weird_walking_event_timer: float = 0
    destroying_event_timer: float = 0
    current_speed: int = 0
    scores: list[int] = field(default_factory=list)

    def init(self, diameter, number_of_players, initial_speed):
        radius = diameter / 2
        color = Color.players_colors()
        for _ in range(number_of_players):
            player = Snake.at_random_position(radius)
            player.color = next(color)
            self.players.append(player)
        self.fruits=[Fruit.at_random_position(radius) for _ in range(6)]
        self.current_speed= initial_speed
        self.scores=[0] * number_of_players

    def alive_players(self):
        return filter(lambda x: x.alive, self.players)
    
    def enumarate_alive_players(self):
        for idx, player in enumerate(self.players):
            if player.alive:
                yield idx, player

    def all_players_dead(self):
        return all(not player.alive for player in self.players)

    def reset(self):
        self.players = []
        self.fruits = []
        self.walls = []
        self.time_passed = 0
        self.fruit_event_timer = 0
        self.wall_event_timer = 0
        self.wall_walking_event_timer = 0
        self.weird_walking_event_timer = 0
        self.destroying_event_timer = 0
        self.current_speed = 0
        self.scores = []

    def to_json(self):
        return {
            "players": [player.to_json() for player in self.players],
            "fruits": [fruit.to_json() for fruit in self.fruits],
            "walls": [wall.to_json() for wall in self.walls],
            "time_passed": self.time_passed,
            "fruit_event_timer": self.fruit_event_timer,
            "wall_event_timer": self.wall_event_timer,
            "wall_walking_event_timer": self.wall_walking_event_timer,
            "weird_walking_event_timer": self.weird_walking_event_timer,
            "destroying_event_timer": self.destroying_event_timer,
            "current_speed": self.current_speed,
            "scores": self.scores
        }
    
    @classmethod
    def from_json(cls, data):
        return cls(
            players=[Snake.from_json(player) for player in data["players"]],
            fruits=[Fruit.from_json(fruit) for fruit in data["fruits"]],
            walls=[Wall.from_json(wall) for wall in data["walls"]],
            time_passed=data["time_passed"],
            fruit_event_timer=data["fruit_event_timer"],
            wall_event_timer=data["wall_event_timer"],
            wall_walking_event_timer=data["wall_walking_event_timer"],
            weird_walking_event_timer=data["weird_walking_event_timer"],
            destroying_event_timer=data["destroying_event_timer"],
            current_speed=data["current_speed"],
            scores=data["scores"]
        )
    
    def copy_values(self, other):
        self.players = other.players
        self.fruits = other.fruits
        self.walls = other.walls
        self.time_passed = other.time_passed
        self.fruit_event_timer = other.fruit_event_timer
        self.wall_event_timer = other.wall_event_timer
        self.wall_walking_event_timer = other.wall_walking_event_timer
        self.weird_walking_event_timer = other.weird_walking_event_timer
        self.destroying_event_timer = other.destroying_event_timer
        self.current_speed = other.current_speed
        self.scores = other.scores