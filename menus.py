import client
from dto import *
import host
from views import *
import functools as ft
import pygameview


def main_menu():
    async def play():
        game_state = GameState()
        game_state.init(Config().number_of_players)

        await ReadyGoView(game_state, GameView(game_state))
        scores = game_state.scores

        # save scores
        if Game().time_limit:
            with open("leaderboard.data", "a") as file:
                for idx, score in enumerate(scores):
                    file.write(f"{Config().names[idx]}: {score}\n")
                names_combined = " + ".join(sorted(Config().active_players_names))
                file.write(f"{names_combined}: {sum(scores)}\n")
        await show_scores(scores, Config().names)

        Config().save_to_file()

    menu_options = ["PLAY"]
    menu_methods = [play]

    modes = ["1 MINUTE", "ENDLESS"]
    async def change_mode(): Game().time_limit = 0 if Game().time_limit else 60
    menu_options += [f"MODE: {modes[0] if Game().time_limit else modes[1]}"]
    menu_methods += [change_mode]


    next_mode = (Config().number_of_players) % 3 +1
    async def change_players_num(): Config().number_of_players = next_mode
    menu_options += [f"{Config().number_of_players} PLAYER{'S' if Config().number_of_players > 1 else ''}"]
    menu_methods += [change_players_num]


    async def change_name(which_player):
        result = await pygameview.common.InputView("Write your name:", Config().names[which_player], lambda ch: not ch in " +:")
        if result: Config().names[which_player] = result
    for i in range(Config().number_of_players):
        menu_options += [f"PLAYER {i+1}: {Config().names[i]}"]
        menu_methods += [ft.partial(change_name, i)]
        
    resolution_phrase = "RESOLUTION: "
    if pygame.display.get_window_size() == pygameutils.get_screen_size():
        resolution_phrase += "FULLSCREEN"
    else:
        resolution_phrase += "x".join(str(i) for i in pygame.display.get_window_size())
    async def leaderboard(): await pygameview.common.ScrollableView("LEADERBOARD", read_leaderboard_file("leaderboard.data"))
    async def resolution(): pygameutils.next_screen_resolution()
    controls = ft.partial(pygameview.common.show_menu, "CONTROLS", controls_menu)
    network = ft.partial(pygameview.common.show_menu, "NETWORK", network_menu)
    menu_options += ["LEADERBOARD", "CONTROLS", resolution_phrase, "NETWORK"]
    menu_methods += [leaderboard, controls, resolution, network]

    return menu_options, menu_methods

def controls_menu():
    menu_options = []
    menu_methods = []

    async def left(which_player):
        key = await pygameview.common.KeyInputView("Press a key...")
        if key: Config().controls[which_player].left = key
    async def right(which_player):
        key = await pygameview.common.KeyInputView("Press a key...")
        if key: Config().controls[which_player].right = key

    for idx, control in enumerate(Config().controls):
        menu_options += [f"PLAYER {idx+1} LEFT: {pygame.key.name(control.left)}"]
        menu_options += [f"PLAYER {idx+1} RIGHT: {pygame.key.name(control.right)}"]
        menu_methods += [ft.partial(left, idx), ft.partial(right, idx)]
    return menu_options, menu_methods

def network_menu():
    async def join():
        host_address_phrase = await pygameview.common.InputView("Enter host address:", Config().last_connected_ip)
        if not host_address_phrase: return
        parts = host_address_phrase.split(":")
        ip = parts[0]
        
        port = int(parts[1]) if len(parts) > 1 else DEFAULT_PORT
        await client.run_client((ip, port))
    
    menu_options = ["CREATE ROOM", "JOIN"]
    menu_methods = [host.run_host, join]
    return menu_options, menu_methods