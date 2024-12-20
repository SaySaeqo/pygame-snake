import asyncio
import gamenetwork as net
from views import *
import utils
import dto
import constants


class HostNetworkListener(net.NetworkListener):

    def __init__(self, address, local_players: list, game_state: dto.GameState):
        super().__init__(address)
        self.players = local_players
        self.game_state = game_state

    def action_join(self, names):
        constants.LOG.info(f"Player joined: {names}")
        new_players = [[name, self.address] for name in names]
        self.players.extend(new_players)

    def action_control(self, data):
        try:
            idx = utils.find_index(self.players, lambda x: x[0] == data["name"] and x[1] == self.address)
            player = self.game_state.players[idx]
            player.decision = data["direction"]
        except StopIteration:
            pass

    def disconnected(self):
        constants.LOG.info("Player disconnected")
        for i in range(len(self.players)):
            if self.players[i][1] == self.address:
                del self.players[i]
        

async def run_host():
    server_address = ("0.0.0.0", constants.DEFAULT_PORT)
    host = f"{utils.get_my_ip()}:{server_address[1]}"
    players = [[name, server_address] for name in dto.Config().active_players_names]
    game_state = dto.GameState()

    with net.ContextManager():
        try:
            await net.start_server(server_address, lambda address: HostNetworkListener(address, players, game_state))
        except OSError as e:
            constants.LOG.warning(f"Could not start the server: {e}")
            return
        
        while True:
            should_start = await LobbyView(host, players)
            if not should_start: return

            dto.Config().save_to_file()
            game_state.init(len(players))
            net.send("start", pygame.display.get_window_size())
            await ReadyGoView(game_state,GameView(game_state))
            players_copy = players.copy()
            players.clear()
            players.extend([name, server_address] for name in dto.Config().active_players_names)
            net.send("score", game_state.to_json())
            await show_scores(game_state.scores, players_copy)
            game_state.reset()


lobby_running = True

class SoloHostNetworkListener(HostNetworkListener):
    def action_start(self, resolution):
        if self.players and self.address == self.players[0][1] and not self.game_state.get_init():
            constants.Game().screen_rect = pygame.Rect((0, 0), resolution)
            self.game_state.init(self.players)
            net.send("start", resolution)
            global lobby_running
            lobby_running = False

async def solo_host_lobby(players):
    clock = pygameview.AsyncClock()
    global lobby_running
    lobby_running = True
    while lobby_running:
        await clock.tick(pygameview.DEFAULT_FPS)
        net.send_udp("lobby", players)

async def run_solo_host():
    pygame.init()
    server_address = ("0.0.0.0", constants.DEFAULT_PORT)
    players = []
    game_state = dto.GameState()

    with net.ContextManager():
        try:
            await net.start_server(server_address, lambda address: SoloHostNetworkListener(address, players, game_state))
        except OSError as e:
            constants.LOG.warning(f"Could not start the server: {e}")
            return
        
        while True:
            constants.LOG.info("Waiting for players")
            await solo_host_lobby(players)
            constants.LOG.info("Starting the game")
            await solo_host_game(game_state)
            players.clear()
            net.send("score", game_state.to_json())
            game_state.reset()