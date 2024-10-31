import MyPodSixNet as net
from utils import *
from snake_utils import *
import windowfunctions
import apygame
from singleton_decorator import singleton
from dataclasses import dataclass
import decisionfunctions
from icecream import ic

@singleton
@dataclass
class ClientNetworkData:
    players = []
    gameState: GameState = None


class LobbyView(apygame.PyGameView):

    def __init__(self, host_address, conn: net.EndPoint):
        self.host_address = host_address
        self.conn = conn

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
        
    async def async_operation(self):
        self.conn.send("get_lobby_data")
        await self.conn.pump()
        


class GameView(apygame.PyGameView):

    def __init__(self, conn: net.EndPoint):
        self.conn = conn
        self.after_readygo = False

    def update(self):
        draw_board(ClientNetworkData().gameState)

    async def async_operation(self):
        self.conn.send("get_game_data")
        await self.conn.pump()

        if not self.after_readygo and ClientNetworkData().gameState:
            await ready_go(ClientNetworkData().gameState)
            self.after_readygo = True


class ClientNetworkListener(net.NetworkListener):
    

    def __init__(self, conn, local_players_names: list, control_functions: list):
        super().__init__(conn)
        self.local_players_names = local_players_names
        self.control_functions = control_functions
        self.snake_tasks = []

    def Network_lobby(self, players):
        ClientNetworkData().players = players

    def Network_game(self, game_state):
        ClientNetworkData().gameState = GameState.from_json(game_state)

    def Network_start(self, options):
        log().info("Game is starting")
        options = Options.from_json(options)
        pygame.display.set_mode(options.resolution)
        self.snake_tasks = [asyncio.create_task(decisionfunctions.send_decision(self.conn, name, options.fps, function))
                            for name, function in zip(self.local_players_names, self.control_functions)]
        apygame.setView(GameView(self.conn))

    def Network_score(self, game_state):
        for task in self.snake_tasks:
            task.cancel()
        game_state = GameState.from_json(game_state)
        log().info("Game over")
        show_scores(game_state.scores, ClientNetworkData().players)
        apygame.setView(LobbyView(str(self.conn.address), self.conn))

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

    client.send("join", local_players_names)

    apygame.setView(LobbyView(host_address, client))

    await apygame.init(fps=60)

    del client

