import asyncio
import gamenetwork as net
from views import *
import utils
import dto
import constants
import logging

import gamenetwork.server_tester as server_tester
class HostNetworkListener(server_tester.ServerTester):

    def __init__(self, local_players: list, game_state: dto.GameState):
        self.players = local_players
        self.game_state = game_state

    def action_join(self, names):
        constants.LOG.info(f"Player joined: {names}")
        new_players = [[name, self._id] for name in names]
        self.players.extend(new_players)

    def action_control(self, data):
        try:
            idx = utils.find_index(self.players, lambda x: x[0] == data["name"] and x[1] == self._id)
            player = self.game_state.players[idx]
            if self.game_state.time_passed < data["time_passed"]:
                add_control(player, data["direction"], data["time_passed"])
        except StopIteration:
            pass

    def disconnected(self):
        constants.LOG.info("Player disconnected")
        for i in range(len(self.players)):
            if self.players[i][1] == self._id:
                del self.players[i]
        

async def run_host():
    host = f"{utils.get_my_ip()}:{constants.DEFAULT_PORT}"
    players = [[name, "host"] for name in dto.Config().active_players_names]
    game_state = dto.GameState()

    with net.ContextManager():
        try:
            await net.start_server("0.0.0.0", constants.DEFAULT_PORT, constants.DEFAULT_PORT, HostNetworkListener(players, game_state))
        except OSError as e:
            constants.LOG.warning(f"Could not start the server: {e}")
            return
        
        while True:
            should_start = await LobbyView(host, players)
            if not should_start: return

            dto.Config().save_to_file()
            game_state.init(len(players))
            for snake, (name, _id) in zip(game_state.players, players):
                net.send("your_color", {"name": name, "color": snake.color}, to=_id)
            net.send("start", pygame.display.get_window_size())
            await ReadyGoView(game_state,GameView(game_state))
            players_copy = players.copy()
            players.clear()
            players.extend([name, "host"] for name in dto.Config().active_players_names)
            net.send("score", game_state.serialize())
            await show_scores(game_state.scores, players_copy)
            game_state.reset()


lobby_running = True

class SoloHostNetworkListener(HostNetworkListener):
    def action_start(self, resolution):
        constants.LOG.debug(f"Start request received with resolution: {resolution}")
        if self.players and self._id == self.players[0][1] and not self.game_state.get_init():
            constants.Game().screen_rect = pygame.Rect((0, 0), resolution)
            self.game_state.init(len(self.players))
            for snake, (name, _id) in zip(self.game_state.players, self.players):
                net.send("your_color", {"name": name, "color": snake.color}, to=_id)
            net.send("start", resolution)
            global lobby_running
            lobby_running = False
    def action_set_latency(self, latency):
        constants.LOG.debug(f"Setting latency to {latency} ms")
        constants.NETWORK_GAME_LATENCY = int(latency)
    def action_game_send_udp(self, data):
        global SEND_UDP
        constants.LOG.debug(f"Sending UDP states set to: {SEND_UDP}")
        SEND_UDP = not SEND_UDP

async def solo_host_lobby(players):
    clock = pygameview.AsyncClock()
    global lobby_running
    lobby_running = True
    LOBBY_FPS = 10
    while lobby_running:
        await clock.tick(LOBBY_FPS)
        net.send_udp("lobby", players)

async def run_solo_host():
    tcp_port = int(sys.argv[1]) if len(sys.argv) > 1 else constants.DEFAULT_PORT
    udp_port = int(sys.argv[2]) if len(sys.argv) > 2 else constants.DEFAULT_PORT
    pygame.init()
    players = []
    game_state = dto.GameState()

    with net.ContextManager():
        try:
            await net.start_server("0.0.0.0", tcp_port, udp_port, SoloHostNetworkListener(players, game_state))
        except OSError as e:
            constants.LOG.warning(f"Could not start the server: {e}")
            return
        
        while True:
            constants.LOG.info("Waiting for players")
            await solo_host_lobby(players)
            constants.LOG.info("Starting the game")
            await solo_host_game(game_state)
            players.clear()
            net.send("score", game_state.serialize())
            game_state.reset()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, filename="host.log", filemode="w")
    server_tester.LOG_FILE = "host.log"
    try:
        print("Starting solo host...")
        asyncio.run(run_solo_host())
    except KeyboardInterrupt:
        print("Solo host stopped by user.")