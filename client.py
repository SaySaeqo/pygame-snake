import gamenetwork as net
import snake_utils
from utils import *
from snake_utils import *
import windowfunctions
import apygame
from singleton_decorator import singleton
from dataclasses import dataclass
import decisionfunctions

@singleton
@dataclass
class ClientNetworkData:
    players = []
    game_state: GameState = None


class LobbyView(apygame.PyGameView):

    def __init__(self, host_address):
        self.host_address = host_address

    def update(self, delta):
        players_phrase = ""
        for player in ClientNetworkData().players:
            players_phrase += f"{player})\n"
        
        SOME_OFFSET = 30
        windowfunctions.MenuDrawer(SOME_OFFSET)\
            .draw("Network Room", 72)\
            .add_space(SOME_OFFSET)\
            .draw(f"Host: {self.host_address[0]}:{self.host_address[1]}", 24)\
            .add_space(SOME_OFFSET*2)\
            .draw(players_phrase)
        
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                apygame.closeView()
        super().handle_event(event)


class ClientGameView(apygame.PyGameView):

    def update(self, delta):
        draw_board(ClientNetworkData().game_state)

class ClientReadyGoView(snake_utils.ReadyGoView):

    def __init__(self, next_view: apygame.PyGameView):
        super().__init__(ClientNetworkData().game_state, next_view)

    def update(self, delta):
        self.state = ClientNetworkData().game_state
        super().update(delta)

    async def do_async(self):
        pass


class ClientNetworkListener(net.NetworkListener):
    
    def __init__(self, address, local_players_names: list, control_functions: list):
        super().__init__(address)
        self.local_players_names = local_players_names
        self.control_functions = control_functions
        self.snake_tasks = []

    def action_lobby(self, players):
        ClientNetworkData().players = players

    def action_game(self, game_state):
        ClientNetworkData().game_state = GameState.from_json(game_state)

    def action_start(self, resolution):
        log().info("Game is starting")
        pygame.display.set_mode(resolution, pygame.FULLSCREEN if resolution == get_screen_size() else 0)
        self.snake_tasks = [asyncio.create_task(decisionfunctions.send_decision(self.address, name, function))
                            for name, function in zip(self.local_players_names, self.control_functions)]
        apygame.setView(ClientReadyGoView(ClientGameView()))

    def action_score(self, game_state):
        for task in self.snake_tasks:
            task.cancel()
        game_state = GameState.from_json(game_state)
        log().info("Game over")
        show_scores(game_state.scores, ClientNetworkData().players)
        net.send("join", self.local_players_names)
        apygame.setView(LobbyView(self.address))

    def disconnected(self):
        log().info("Disconnected from the server")
        apygame.closeView()

async def run_client(host_address: tuple[str, int], local_players_names: list, control_functions: list):
    try:
        await first_completed(
            net.connect_to_server(host_address, lambda address: ClientNetworkListener(address, local_players_names, control_functions)),
            apygame.run_async(WaitingView("Connecting to server"))
            )
    except OSError as e:
        log().error(e)
        log().info("Could not connect to the server")
        return
    finally:
        await apygame.wait_closed()
    
    if not net.is_connected(host_address):
        log().info("Connection aborted")
        return
        
    net.send("join", local_players_names)
    await LobbyView(host_address)
    net.close()
    

    

