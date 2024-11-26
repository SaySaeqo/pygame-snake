from dataclasses import dataclass
import client
from decisionfunctions import based_on_keys, control_snake
from dto import *
import host
from snake_utils import *
from windowfunctions import *
import asyncio
import functools as ft


async def show_menu(title, menu):
    choice = 0
    while True:
        options, methods = menu()
        choice = await MenuView(title, options, choice)
        if choice == None: break
        await methods[choice]()

class SnakeMenu:

    @dataclass
    class Control:
        left: int
        right: int 

    def __init__(self) -> None:
        self.names = ["snake", "snake2", "snake3"]
        self.number_of_players = 1
        self.controls = [self.Control(pygame.K_LEFT, pygame.K_RIGHT), self.Control(pygame.K_a, pygame.K_d), self.Control(pygame.K_j, pygame.K_l)]
        self.load_config()
        create_window("Snake")

    @property
    def control_functions(self):
        return [based_on_keys(control.left, control.right) for control in self.controls]

    def main_menu(self):
        async def play(): 
            options = Options()
            game_state = GameState()
            game_state.init(options.diameter, self.number_of_players, options.speed)

            for snake, func in zip(game_state.players, self.control_functions):
                asyncio.create_task(control_snake(func, snake, options.fps))

            await ReadyGoView(game_state, GameView(game_state, options))
            scores = game_state.scores

            # save scores
            with open("leaderboard.data", "a") as file:
                for idx, score in enumerate(scores):
                    file.write(f"{self.names[idx]}: {score}\n")
                names_combined = " + ".join(sorted(self.names[:self.number_of_players]))
                file.write(f"{names_combined}: {sum(scores)}\n")
            show_scores(scores, self.names)

            self.save_config()

        menu_options = ["PLAY"]
        menu_methods = [play]

        next_mode = (self.number_of_players) % 3 +1
        async def change_mode(): self.number_of_players = next_mode
        menu_options += [f"{next_mode} PLAYER MODE"]
        menu_methods += [change_mode]


        async def change_name(which_player):
            result = await InputView("Write your name:", self.names[which_player], lambda ch: not ch in " +:")
            if result: self.names[which_player] = result
        for i in range(self.number_of_players):
            menu_options += [f"PLAYER {i+1}: {self.names[i]}"]
            menu_methods += [ft.partial(change_name, i)]
            
        resolution_phrase = "RESOLUTION: "
        if pygame.display.get_window_size() == get_screen_size():
            resolution_phrase += "FULLSCREEN"
        else:
            resolution_phrase += "x".join(str(i) for i in pygame.display.get_window_size())
        async def leaderboards(): await ScrollableView("LEADERBOARD", read_leaderboard_file("leaderboard.data"))
        async def resolution(): next_screen_resolution()
        async def network():
            subchoice = 0
            while True:
                subchoice = await MenuView("NETWORK", ["CREATE ROOM", "JOIN"], subchoice)
                if subchoice == None: break
                elif subchoice == 0:
                    await host.run_host(self.names[:self.number_of_players], Options(), self.control_functions)
                elif subchoice == 1:
                    host_address_phrase = await InputView("Enter host address:", "localhost")
                    if host_address_phrase:
                        separator = ":" if ":" in host_address_phrase else ";"
                        parts = host_address_phrase.split(separator)
                        ip = parts[0]
                        port = int(parts[1]) if len(parts) > 1 else 31426
                        await client.run_client((ip, port), self.names[:self.number_of_players], self.control_functions)
        menu_options += ["LEADERBOARD", "CONTROLS", resolution_phrase, "NETWORK"]
        menu_methods += [leaderboards, ft.partial(show_menu, "CONTROLS", self.controls_menu), resolution, network]

        return menu_options, menu_methods
    
    def controls_menu(self):
        menu_options = []
        menu_methods = []

        async def left(which_player):
            key = await KeyInputView("Press a key...")
            if key: self.controls[which_player].left = key
        async def right(which_player):
            key = await KeyInputView("Press a key...")
            if key: self.controls[which_player].right = key

        for idx, control in enumerate(self.controls):
            menu_options += [f"PLAYER {idx+1} LEFT: {pygame.key.name(control.left)}"]
            menu_options += [f"PLAYER {idx+1} RIGHT: {pygame.key.name(control.right)}"]
            menu_methods += [ft.partial(left, idx), ft.partial(right, idx)]
        return menu_options, menu_methods
    
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

    async def show(self):
        await show_menu("SNAKE", self.main_menu)
                