import asyncio
import gamenetwork as net
from views import *
import utils
import dto
import constants
import logging


class HostNetworkListener(net.NetworkListener):

    def __init__(self, address, local_players: list, game_state: dto.GameState):
        super().__init__(address)
        self.players = local_players
        self.game_state = game_state

    def action_join(self, names):
        constants.LOG.info(f"Player joined: {names}")
        new_players = [[name, self._address] for name in names]
        self.players.extend(new_players)

    def action_control(self, data):
        try:
            idx = utils.find_index(self.players, lambda x: x[0] == data["name"] and x[1] == self._address)
            player = self.game_state.players[idx]
            player.decision = data["direction"]
        except StopIteration:
            pass

    def disconnected(self):
        constants.LOG.info("Player disconnected")
        for i in range(len(self.players)):
            if self.players[i][1] == self._address:
                del self.players[i]

    def action_respond(self, msg):
        net.send("print", f"Message '{msg}' have got sent back by TCP.")
        net.send_udp("print", f"Message '{msg}' have got sent back by UDP.")
        

async def run_host():
    host = f"{utils.get_my_ip()}:{constants.DEFAULT_PORT}"
    players = [[name, "host"] for name in dto.Config().active_players_names]
    game_state = dto.GameState()

    with net.ContextManager():
        try:
            await net.start_server("0.0.0.0", constants.DEFAULT_PORT, constants.DEFAULT_PORT, lambda address: HostNetworkListener(address, players, game_state))
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
            players.extend([name, "host"] for name in dto.Config().active_players_names)
            net.send("score", game_state.to_json())
            await show_scores(game_state.scores, players_copy)
            game_state.reset()


lobby_running = True

class SoloHostNetworkListener(HostNetworkListener):
    def action_start(self, resolution):
        if self.players and self._address == self.players[0][1] and not self.game_state.get_init():
            constants.Game().screen_rect = pygame.Rect((0, 0), resolution)
            self.game_state.init(len(self.players))
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
    tcp_port = int(sys.argv[1]) if len(sys.argv) > 1 else constants.DEFAULT_PORT
    udp_port = int(sys.argv[2]) if len(sys.argv) > 2 else constants.DEFAULT_PORT
    pygame.init()
    players = []
    game_state = dto.GameState()

    with net.ContextManager():
        try:
            await net.start_server("0.0.0.0", tcp_port, udp_port, lambda address: SoloHostNetworkListener(address, players, game_state))
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

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, filename="snake_host.log", filemode="w")
    asyncio.run(run_solo_host())