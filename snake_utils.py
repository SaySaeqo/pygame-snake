import sys
import pygame
from gameobjects import Fruit, Snake, Wall
from constants import Color
from windowfunctions import *
from dataclasses import dataclass, field
from decisionfunctions import based_on_keys
from asyncclock import Clock
import MyPodSixNet as net
import logging
import constants

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


def initialize_players(diameter, number):
    players = [Snake.at_random_position(diameter / 2) for _ in range(number)]
    for i in range(number):
        players[i].color = constants.get_color(i)
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
    destroying_event_timer: float = 0
    current_speed: int = 0
    scores: list[int] = field(default_factory=list)

    def alive_players(self):
        return list(filter(lambda x: x.alive, self.players))

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
    
    def to_bytes(self):\
        return json.dumps(self.to_json()).encode()
    
    @classmethod
    def from_bytes(cls, data: bytes):
        return cls.from_json(json.loads(data.decode()))


def draw_board(state: GameState):
        pygame.display.get_surface().fill(Color.black)
        if not state:
            title("NO GAME STATE\n(error)", offset=10)
            return
        
        # draw game objects
        for player in state.alive_players():
            player.draw()
        for fruit in state.fruits:
            fruit.draw()
        for wall in state.walls:
            wall.draw()

        # draw wall
        if state.wall_walking_event_timer == 0:
            pygame.draw.rect(pygame.display.get_surface(), Color.cyan, pygame.display.get_surface().get_rect(), 1)

        # draw time and score
        time_phrase = "TIME: "
        time_phrase += f"{int(state.time_passed / 60)}:{int(state.time_passed) % 60:02d}" if state.time_passed >= 60 else f"{int(state.time_passed)}"
        score_phrase = f"SCORE: {sum(state.scores)}"
        title(time_phrase + "\n" + score_phrase, offset=10)

        # draw arrows for 1st 2 seconds
        if state.time_passed < 2:
            for player in state.alive_players():
                player.draw_direction()

def show_scores(scores, names):
    end_phrase = "GAME OVER\n"
    end_phrase += f"TOTAL SCORE: {sum(scores)}\n"
    for idx, score in enumerate(scores):
        end_phrase += f"{names[idx]}: {score}\n"
    pause(end_phrase)

async def run_game(st: GameState, options=Options()):

    create_window("Snake")

    # region GAME_STATE
    # initialize game objects
    st.fruits=[Fruit.at_random_position(options.diameter / 2) for _ in range(6)]
    # initialize game variables
    st.current_speed=options.speed
    st.scores=[0] * len(st.players)
    # endregion
    draw_board(st)

    # first_completed(wait_screen("waiting", asyncio.wait(2)))

    # region READY?
    title("READY?", Align.CENTER)
    pygame.display.update()
    pygame.time.wait(666)
    draw_board(st)
    # endregion
    # region GO!
    title("GO!", Align.CENTER, 144)
    pygame.display.update()
    pygame.time.wait(333)
    draw_board(st)
    # endregion

    # inner main loop
    clock = Clock()
    while True:
        # displaying view
        draw_board(st)
        pygame.display.update()

        # pygame "must-have" + pausing
        fps = options.fps
        frame_time = 1 / fps
        await clock.tick(fps)
        events = pygame.event.get()
        should_pause = False
        for event in events:
            if event.type == pygame.KEYDOWN and \
                    event.key in (pygame.K_p, pygame.K_PAUSE, pygame.K_SPACE):
                should_pause = True
            if event.type == pygame.QUIT:
                sys.exit()
        if should_pause:
            # TODO pause crashes games
            pause()
            draw_board(st)

        for idx, player in enumerate(st.alive_players()):
            player.move(options.diameter * st.current_speed / fps, should_walk_weird=(st.weird_walking_event_timer > 0))
            # region COLLISION_CHECK
            # with fruits
            for fruit in st.fruits:
                if fruit.is_colliding_with(player):
                    if fruit.gives_wall_walking:
                        st.wall_walking_event_timer += 5
                    if fruit.gives_weird_walking:
                        st.weird_walking_event_timer += 15
                    if fruit.gives_wall_walking and fruit.gives_weird_walking:
                        st.destroying_event_timer += 5
                    player.consume(fruit)
                    st.scores[idx] += 1
                    # TODO wynik zapisuje sie dla pierwszego gracza, nawet jeśli drugi zje owoc a pierwszy już nie żyje
            # with walls
            for wall in st.walls:
                if wall.is_colliding_with(player):
                    if st.destroying_event_timer > 0:
                        pygame.mixer.Sound("crush.mp3").play(maxtime=1000)
                        st.walls.remove(wall)
                    else:
                        player.died()
                        print("Clash with wall")
            # with borders
            if not pygame.display.get_surface().get_rect().contains(player.get_rect()):
                if (st.wall_walking_event_timer == 0):
                    player.died()
                    print("Out of border")
                else:
                    player.x = (player.x + pygame.display.get_surface().get_rect().width) % pygame.display.get_surface().get_rect().width
                    player.y = (player.y + pygame.display.get_surface().get_rect().height) % pygame.display.get_surface().get_rect().height
            # with tail
            for pl in st.alive_players():
                if player.is_colliding_with(pl):
                    player.died()
                    print("Clash with tail")
            # endregion
        if len(st.alive_players()) == 0:
            return st.scores

        # update time counter
        st.time_passed += frame_time
        st.fruit_event_timer += frame_time
        st.wall_walking_event_timer = max(0, st.wall_walking_event_timer - frame_time)
        st.weird_walking_event_timer = max(0, st.weird_walking_event_timer - frame_time)
        st.destroying_event_timer = max(0, st.destroying_event_timer - frame_time)
        if st.fruit_event_timer > 5:
            st.fruits.append(Fruit.at_random_position(options.diameter / 2))
            st.fruit_event_timer = 0
        if st.time_passed > options.time_limit:
            st.wall_event_timer += frame_time
            if st.wall_event_timer > (options.time_limit**2) / (st.time_passed**2):
                st.walls += [Wall.at_random_position(options.diameter)]
                st.wall_event_timer = 0

        # something to make it more fun!
        st.current_speed = options.speed + 2 * int(1 + st.time_passed / 10)
        for player in st.alive_players():
            player.rotation_power = options.rotation_power + int(st.time_passed / 10)

class SnakeMenu:

    @dataclass
    class Control:
        left: int
        right: int

    @dataclass
    class NetworkData:
        is_host: bool = True
        is_active: bool = False
        host_address: net.NetworkAddress = field(default_factory=lambda: net.NetworkAddress("localhost", 1234))

    

    def __init__(self) -> None:
        self.names = ["snake", "snake2", "snake3"]
        self.number_of_players = 1
        self.controls = [self.Control(pygame.K_LEFT, pygame.K_RIGHT), self.Control(pygame.K_a, pygame.K_d), self.Control(pygame.K_j, pygame.K_l)]
        self.network = self.NetworkData()
        self.choice = 0
        self.load_config()
        create_window("Snake")

    @property
    def control_functions(self):
        return [based_on_keys(control.left, control.right) for control in self.controls]

    @property
    def menu_options(self):
        menu_options = ["PLAY"]
        next_mode = (self.number_of_players) % 3 +1
        menu_options += [f"{next_mode} PLAYER MODE"]
        for i in range(self.number_of_players):
            menu_options += [f"PLAYER {i+1}: {self.names[i]}"]
        resolution_phrase = "RESOLUTION: "
        resolution_phrase += "FULLSCREEN" if pygame.display.get_window_size() == get_screen_size() else f"{pygame.display.get_window_size()[0]}x{pygame.display.get_window_size()[1]}"
        menu_options += ["LEADERBOARD", "CONTROLS", resolution_phrase, "NETWORK", "EXIT"]
        return menu_options
    
    @property
    def controls_submenu_options(self):
        menu_options = []
        for i in range(len(self.controls)):
            menu_options += [f"PLAYER {i+1} LEFT: {pygame.key.name(self.controls[i].left)}"]
            menu_options += [f"PLAYER {i+1} RIGHT: {pygame.key.name(self.controls[i].right)}"]
        menu_options += ["BACK"]
        return menu_options
    
    def save_config(self):
        with open("config.data", "w") as file:
            for idx, name in enumerate(self.names):
                file.write(f"player {idx+1} name: {name}\n")
            for control in self.controls:
                file.write(f"player {self.controls.index(control)+1} controls: {pygame.key.name(control.left)} {pygame.key.name(control.right)}\n")
            file.write(f"resolution: {pygame.display.get_window_size()[0]} {pygame.display.get_window_size()[1]}\n")

    def load_config(self):
        try:
            with open("config.data", "r") as file:
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
                        parts = line.split()
                        create_window("Snake", int(parts[1]), int(parts[2]))
        except FileNotFoundError:
            ...

    def run(self):
        while True:
            self.choice, option = menu("SNAKE", self.menu_options, self.choice)
            if option == "PLAY":
                self.save_config()
                return
            if option == "EXIT":
                sys.exit()
            if option == "LEADERBOARD":
                leaderboard("leaderboard.data")
            if option.startswith("PLAYER "):
                which_player = int(option[7]) - 1
                result = inputbox("Write your name:", self.names[which_player], lambda ch: not ch in " +:")
                if result: self.names[which_player] = result
            if option.count("PLAYER MODE") > 0:
                self.number_of_players = int(option[0])
            if option.startswith("RESOLUTION:"):
                next_screen_resolution()
            if option == "CONTROLS":
                subchoice = 0
                while True:
                    subchoice, suboption = menu("CONTROLS", self.controls_submenu_options, subchoice)
                    if suboption == "BACK":
                        break
                    if suboption.startswith("PLAYER "):
                        which_player = int(suboption[7]) - 1
                        result = keyinputbox("Press a key...")
                        if result:
                            if suboption.count("LEFT:") > 0:
                                self.controls[which_player].left = result
                            else:
                                self.controls[which_player].right = result
            if option == "NETWORK":
                subchoice = 0
                while True:
                    subchoice, suboption = menu("NETWORK", ["CREATE ROOM", "JOIN", "BACK"], subchoice)
                    if suboption == "BACK":
                        break
                    if suboption == "CREATE ROOM":
                        self.network.is_host = True
                        self.network.is_active = True
                        return
                    if suboption == "JOIN":
                        self.network.is_host = False
                        self.network.is_active = True
                        host_address_phrase = inputbox("Enter host address:", "localhost")
                        if host_address_phrase:
                            separator = ":" if ":" in host_address_phrase else ";"
                            parts = host_address_phrase.split(separator)
                            ip = parts[0]
                            port = int(parts[1]) if len(parts) > 1 else 31426
                            self.network.host_address = net.NetworkAddress(ip, port)
                        return