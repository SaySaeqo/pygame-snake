import gamenetwork as net
import views
from utils import *
from views import *
import pygameview
from dataclasses import dataclass
from dto import Config, GameState
import constants
import pygameutils
import socket

@singleton
@dataclass
class ClientNetworkData:
    players = []
    game_state: GameState = None

should_relaunch = True


class ClientLobbyView(pygameview.PyGameView):

    def __init__(self, host_address):
        self.host_address = host_address
        self.timer = 0

    def update(self, delta):
        self.timer += delta
        players_phrase = ""
        for player in ClientNetworkData().players:
            players_phrase += f"{player})\n"
        
        pygameview.utils.MenuDrawer(pygameview.common.MENU_LINE_SPACING)\
            .draw("Network Room", 72)\
            .add_space(pygameview.common.MENU_LINE_SPACING)\
            .draw(f"Host: {self.host_address[0]}:{self.host_address[1]}", 24)\
            .add_space(pygameview.common.MENU_LINE_SPACING*2)\
            .draw(players_phrase)
        
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygameview.close_view()
            if event.key == pygame.K_RETURN and self.timer > 1:
                net.send("start", pygame.display.get_window_size())
        super().handle_event(event)


class ClientGameView(pygameview.PyGameView):

    def update(self, delta):
        draw_board(ClientNetworkData().game_state)

        for name, function in zip(Config().active_players_names, Config().control_functions):
            net.send("control", {"name": name, "direction": function()})

class ClientReadyGoView(views.ReadyGoView):

    def __init__(self, next_view: pygameview.PyGameView):
        super().__init__(ClientNetworkData().game_state, next_view)

    def update(self, delta):
        self.state = ClientNetworkData().game_state
        super().update(delta)

    async def do_async(self):
        pass


class ClientNetworkListener(net.NetworkListener):

    def action_lobby(self, players):
        ClientNetworkData().players = players

    def action_game(self, game_state):
        ClientNetworkData().game_state = GameState.from_json(game_state)

    def action_start(self, resolution):
        constants.LOG.info("Game is starting")
        pygame.display.set_mode(resolution, pygame.FULLSCREEN if resolution == pygameutils.get_screen_size() else 0)
        pygameview.set_view(ClientReadyGoView(ClientGameView()))

    def action_score(self, game_state):
        game_state = GameState.from_json(game_state)
        constants.LOG.info("Game over")
        pygameview.set_view(show_scores(game_state.scores, ClientNetworkData().players))
        global should_relaunch
        should_relaunch = True
        
    def disconnected(self):
        constants.LOG.info("Disconnected from the server")
        pygameview.close_view()


async def run_client(host_address: tuple[str, int]):
    host_address = socket.gethostbyname(host_address[0]), host_address[1]
    with net.ContextManager():
        try:
            await first_completed(
                net.connect_to_server(host_address, lambda address: ClientNetworkListener(address)),
                pygameview.run_async(pygameview.common.WaitingView("Connecting to server"))
                )
        except OSError as e:
            constants.LOG.warning("Could not connect to the server: {}".format(e))
            return
        finally:
            await pygameview.wait_closed()
        
        if not net.is_connected(host_address):
            constants.LOG.info("Connection aborted")
            return
        
        Config().last_connected_ip = host_address[0]
        Config().save_to_file()

        global should_relaunch
        should_relaunch = True
        while should_relaunch:
            should_relaunch = False
            net.send("join", Config().active_players_names)
            await ClientLobbyView(host_address)
    

    

