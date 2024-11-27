import client
from dto import *
import host
from snake_utils import *
from windowfunctions import *
import functools as ft


async def show_menu(title, menu):
    """
    menu should be function returning tuple of 2 lists:
    - list of options names
    - list of options' couritines to be awaited when chosen
    """
    choice = 0
    while True:
        options, methods = menu()
        choice = await MenuView(title, options, choice)
        if choice == None: break
        await methods[choice]()


def main_menu():
    async def play():
        game_state = GameState()
        game_state.init(Config().number_of_players)

        await ReadyGoView(game_state, GameView(game_state))
        scores = game_state.scores

        # save scores
        with open("leaderboard.data", "a") as file:
            for idx, score in enumerate(scores):
                file.write(f"{Config().names[idx]}: {score}\n")
            names_combined = " + ".join(sorted(Config().active_players_names))
            file.write(f"{names_combined}: {sum(scores)}\n")
        show_scores(scores, Config().names)

        Config().save_to_file()

    menu_options = ["PLAY"]
    menu_methods = [play]

    next_mode = (Config().number_of_players) % 3 +1
    async def change_mode(): Config().number_of_players = next_mode
    menu_options += [f"{next_mode} PLAYER MODE"]
    menu_methods += [change_mode]


    async def change_name(which_player):
        result = await InputView("Write your name:", Config().names[which_player], lambda ch: not ch in " +:")
        if result: Config().names[which_player] = result
    for i in range(Config().number_of_players):
        menu_options += [f"PLAYER {i+1}: {Config().names[i]}"]
        menu_methods += [ft.partial(change_name, i)]
        
    resolution_phrase = "RESOLUTION: "
    if pygame.display.get_window_size() == get_screen_size():
        resolution_phrase += "FULLSCREEN"
    else:
        resolution_phrase += "x".join(str(i) for i in pygame.display.get_window_size())
    async def leaderboard(): await ScrollableView("LEADERBOARD", read_leaderboard_file("leaderboard.data"))
    async def resolution(): next_screen_resolution()
    menu_options += ["LEADERBOARD", "CONTROLS", resolution_phrase, "NETWORK"]
    menu_methods += [leaderboard, ft.partial(show_menu, "CONTROLS", controls_menu), resolution, ft.partial(show_menu, "NETWORK", network_menu)]

    return menu_options, menu_methods

def controls_menu():
    menu_options = []
    menu_methods = []

    async def left(which_player):
        key = await KeyInputView("Press a key...")
        if key: Config().controls[which_player].left = key
    async def right(which_player):
        key = await KeyInputView("Press a key...")
        if key: Config().controls[which_player].right = key

    for idx, control in enumerate(Config().controls):
        menu_options += [f"PLAYER {idx+1} LEFT: {pygame.key.name(control.left)}"]
        menu_options += [f"PLAYER {idx+1} RIGHT: {pygame.key.name(control.right)}"]
        menu_methods += [ft.partial(left, idx), ft.partial(right, idx)]
    return menu_options, menu_methods

def network_menu():
    async def join():
        host_address_phrase = await InputView("Enter host address:", "localhost")
        if not host_address_phrase: return
        parts = host_address_phrase.split(":")
        ip = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 31426
        await client.run_client((ip, port))

    menu_options = ["CREATE ROOM", "JOIN"]
    menu_methods = [host.run_host, join]
    return menu_options, menu_methods