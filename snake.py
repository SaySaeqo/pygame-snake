import sys
import pygame
from gameobjects import Fruit, Snake, Wall
from constants import Color
from windowfunctions import *
from dataclasses import dataclass, field
from decisionfunctions import control_snake, based_on_keys
import asyncio
from asyncclock import Clock
import MyPodSixNet as net
from math import floor
from utils import find_index, first_completed, find, unique
from icecream import ic
import logging
import host
import client
from snake_utils import *

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
        
        if st.wall_walking_event_timer == 0:
            pygame.draw.rect(pygame.display.get_surface(), Color.cyan, pygame.display.get_surface().get_rect(), 1)

        time_phrase = "TIME: "
        time_phrase += f"{int(st.time_passed / 60)}:{int(st.time_passed) % 60:02d}" if st.time_passed >= 60 else f"{int(st.time_passed)}"
        score_phrase = f"SCORE: {sum(st.scores)}"
        title(time_phrase + "\n" + score_phrase, offset=10)
        # draw arrows for 1st 2 seconds
        if st.time_passed < 2:
            for player in st.players:
                player.draw_direction()
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

        for idx, player in enumerate(st.players):
            player.move(options.diameter * st.current_speed / fps, should_walk_weird=(st.weird_walking_event_timer > 0))
            # region COLLISION_CHECK
            # with fruits
            for fruit in st.fruits:
                if fruit.is_colliding_with(player):
                    if fruit.gives_wall_walking:
                        st.wall_walking_event_timer += 5
                    if fruit.gives_weird_walking:
                        st.weird_walking_event_timer += 15
                    player.consume(fruit)
                    st.scores[idx] += 1
                    # TODO wynik zapisuje sie dla pierwszego gracza, nawet jeśli drugi zje owoc a pierwszy już nie żyje
            # with walls
            for wall in st.walls:
                if wall.is_colliding_with(player):
                    if st.weird_walking_event_timer == st.wall_walking_event_timer + 10: #TODO czy to aby na pewno działa?
                        pygame.mixer.Sound("crush.mp3").play(maxtime=1000)
                        st.walls.remove(wall)
                    else:
                        player.died()
                        st.players.remove(player)
                        print("Clash with wall")
            # with borders
            if not pygame.display.get_surface().get_rect().contains(player.get_rect()):
                if (st.wall_walking_event_timer == 0):
                    player.died()
                    st.players.remove(player)
                    print("Out of border")
                else:
                    player.x = (player.x + pygame.display.get_surface().get_rect().width) % pygame.display.get_surface().get_rect().width
                    player.y = (player.y + pygame.display.get_surface().get_rect().height) % pygame.display.get_surface().get_rect().height
            # with tail
            for pl in st.players:
                if player.is_colliding_with(pl):
                    player.died()
                    st.players.remove(player)
                    print("Clash with tail")
            # endregion
        if len(st.players) == 0:
            return st.scores

        # update time counter
        st.time_passed += frame_time
        st.fruit_event_timer += frame_time
        st.wall_walking_event_timer = max(0, st.wall_walking_event_timer - frame_time)
        st.weird_walking_event_timer = max(0, st.weird_walking_event_timer - frame_time)
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
        for player in st.players:
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
                        host_address_phrase = inputbox("Enter host address:", "localhost:1234")
                        if host_address_phrase:
                            separator = ":" if ":" in host_address_phrase else ";"
                            parts = host_address_phrase.split(separator)
                            self.network.host_address = net.NetworkAddress(parts[0], int(parts[1]))
                        return

async def main():
    snake_menu = SnakeMenu()

    while True:
        snake_menu.run()

        options = Options(
            diameter=30,
            speed=4,
            time_limit=60,
            rotation_power=4
        )

        if snake_menu.network.is_active:
            if snake_menu.network.is_host:
                await host.run_host(snake_menu.names, options, snake_menu.control_functions)

                continue
            else:
                # TODO brak systemu obsługi wyjścia z gry po udanym połączeniu
                await client.run_client(snake_menu.network.host_address, snake_menu.names, snake_menu.control_functions)

                continue

        game_state = GameState()
        game_state.players = initialize_players(options.diameter, snake_menu.number_of_players)


        async with asyncio.TaskGroup() as tg:
            for snake, func in zip(game_state.players, snake_menu.control_functions):
                tg.create_task(control_snake(func, snake, options.fps))
            scores = await run_game(game_state, options)

        # save scores
        with open("leaderboard.data", "a") as file:
            for idx, score in enumerate(scores):
                file.write(f"{snake_menu.names[idx]}: {score}\n")
            names_combined = " + ".join(sorted(snake_menu.names[:snake_menu.number_of_players]))
            file.write(f"{names_combined}: {sum(scores)}\n")

        show_scores(scores, snake_menu.names)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    log().info("Starting the game")
    asyncio.run(main())