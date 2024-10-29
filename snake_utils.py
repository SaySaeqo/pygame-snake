import logging
from dataclasses import dataclass, field
import json
import sys
import pygame
from gameobjects import Snake, Fruit, Wall
from constants import Color
from asyncclock import Clock
from windowfunctions import pause

def log():
    return logging.getLogger(__name__)

@dataclass
class Options:
    """
    :param diameter: size of things in pixels
    :param speed: diameters per second
    :param time_limit: seconds
    """
    fps: int = 60
    diameter: int = 10
    speed: int = 8
    time_limit: int = 60
    rotation_power: int = 5

    def to_json(self):
        return {
            "fps": self.fps,
            "diameter": self.diameter,
            "speed": self.speed,
            "time_limit": self.time_limit,
            "rotation_power": self.rotation_power
        }
    
    @classmethod
    def from_json(cls, data):
        return cls(
            fps=data["fps"],
            diameter=data["diameter"],
            speed=data["speed"],
            time_limit=data["time_limit"],
            rotation_power=data["rotation_power"]
        )
    
    def copy_values(self, other):
        self.fps = other.fps
        self.diameter = other.diameter
        self.speed = other.speed
        self.time_limit = other.time_limit
        self.rotation_power = other.rotation_power


def initialize_players(diameter, number):
    players = [Snake.at_random_position(diameter / 2) for _ in range(number)]
    if len(players) > 1:
        players[1].color = Color.red
    if len(players) > 2:
        players[2].color = Color.yellowish
    return players


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
    current_speed: int = 0
    scores: list[int] = field(default_factory=list)

    def reset(self):
        self.players = []
        self.fruits = []
        self.walls = []
        self.time_passed = 0
        self.fruit_event_timer = 0
        self.wall_event_timer = 0
        self.wall_walking_event_timer = 0
        self.weird_walking_event_timer = 0
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
        self.current_speed = other.current_speed
        self.scores = other.scores
    
    def to_bytes(self):\
        return json.dumps(self.to_json()).encode()
    
    @classmethod
    def from_bytes(cls, data: bytes):
        return cls.from_json(json.loads(data.decode()))


def draw_board(state: GameState):
        pygame.display.get_surface().fill(Color.black)
        for player in state.players:
            player.draw()
        for fruit in state.fruits:
            fruit.draw()
        for wall in state.walls:
            wall.draw()


async def only_draw_board(state: GameState, fps: int):
    clock = Clock()
    while True:
        if state:
            draw_board(state)
        await clock.tick(fps)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

def show_scores(scores, names):
    end_phrase = "GAME OVER\n"
    end_phrase += f"TOTAL SCORE: {sum(scores)}\n"
    for idx, score in enumerate(scores):
        end_phrase += f"{names[idx]}: {score}\n"
    pause(end_phrase)