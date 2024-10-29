import MyPodSixNet as net
from utils import *
from snake_utils import *
import windowfunctions
import pygame
import pygame_asyncio
from singleton_decorator import singleton
from dataclasses import dataclass
import decisionfunctions
from icecream import ic

@singleton
@dataclass
class ClientNetworkData:
    players = []
    gameState = None


class LobbyView(pygame_asyncio.PyGameView):

    def __init__(self, host_address):
        self.host_address = host_address

    def update(self):
        players_phrase = ""
        for player in ClientNetworkData().players:
            players_phrase += f"{player})\n"
        
        SOME_OFFSET = 30
        windowfunctions.MenuDrawer(SOME_OFFSET)\
            .draw("Network Room", 72)\
            .add_space(SOME_OFFSET)\
            .draw(f"Host: {self.host_address}", 24)\
            .add_space(SOME_OFFSET*2)\
            .draw(players_phrase)
        


class GameView(pygame_asyncio.PyGameView):

    def update(self):
        only_draw_board(ClientNetworkData().gameState)


class ClientNetworkListener(net.NetworkListener):
    

    def __init__(self, conn, local_players_names: list, control_functions: list):
        super().__init__(conn)
        self.local_players_names = local_players_names
        self.control_functions = control_functions
        self.snake_tasks = []
        self.get_data_task = None

    def set_get_data_task(self, func):
        if self.get_data_task:
            self.get_data_task.cancel()
        log().debug("Setting get_data_task")
        self.get_data_task = asyncio.create_task(func)

    def Network_connected(self, _):
        log().info("Connected to the server")
        async def get_data():
            while True:
                ic("get_lobby_data")
                await self.conn.send_now("get_lobby_data")
                await asyncio.sleep(1)
        log().debug("Setting get_data_task1")
        self.set_get_data_task(get_data())


    def Network_lobby(self, players):
        log().info("Lobby data received")
        ClientNetworkData().players = players

    def Network_game(self, game_state):
        ClientNetworkData().gameState = GameState.from_json(game_state)

    def Network_start(self, options):
        log().info("Game is starting")
        options = Options.from_json(options)
        self.snake_tasks = [asyncio.create_task(decisionfunctions.send_decision(self.conn, name, options.fps, function))
                            for name, function in zip(self.local_players_names, self.control_functions)]
        pygame_asyncio.setView(GameView())
        async def get_data():
            while True:
                await self.conn.send("get_game_data")
                await self.conn.pump()
                await asyncio.sleep(options.fps)
        self.set_get_data_task(get_data())

    def Network_score(self, game_state):
        for task in self.snake_tasks:
            task.cancel()
        self.get_data_task.cancel()
        game_state = GameState.from_json(game_state)
        log().info("Game over")
        show_scores(game_state.scores, game_state.players)

async def run_client(host_address: net.NetworkAddress, local_players_names: list, control_functions: list):
    try:
        client = await first_completed(
            net.connect_to_server(host_address, lambda conn: ClientNetworkListener(conn, local_players_names, control_functions)),
            windowfunctions.wait_screen("Connecting to server")
            )
        if not isinstance(client, net.EndPoint):
            log().info("Connection aborted")
            return
    except OSError as e:
        log().error(e)
        log().info("Could not connect to the server")
        return

    await client.send_now("join", local_players_names)

    pygame_asyncio.setView(LobbyView(host_address))

    await pygame_asyncio.run_pygame_async(fps=60)

    del client

