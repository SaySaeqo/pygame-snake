import asyncio
import MyPodSixNet as net
from decisionfunctions import control_snake
from snake_utils import *
import utils
import windowfunctions
import apygame


class HostNetworkListener(net.NetworkListener):

    def __init__(self, address, local_players: list, game_state: GameState):
        super().__init__(address)
        self.players = local_players
        self.game_state = game_state

    def Network_join(self, names):
        new_players = [[name, str(self.address)] for name in names]
        self.players.extend(new_players)

    def Network_control(self, data):
        idx = utils.find_index(self.players, lambda x: x[0] == data["name"] and x[1] == str(self.address))
        player = self.game_state.players[idx]
        player.decision = data["direction"]

    def Network_disconnected(self):
        log().info("Player disconnected")
        for i in range(len(self.players)):
            if self.players[i][1] == str(self.address):
                del self.players[i]
        
async def run_host(local_players_names: list, options: Options, control_functions: list):
    server_address = net.NetworkAddress(None, 31426)
    host = f"{utils.get_my_ip()}:{server_address.port}"
    local_players_num = len(local_players_names)
    players = [[name, str(server_address)] for name in local_players_names]
    game_state = GameState()

    try:
        await net.start_server(server_address, lambda address: HostNetworkListener(address, players, game_state))
        
        while True:
            should_start = await windowfunctions.network_room(players, host)
            log().debug("Should start: %s", should_start)

            if not should_start:
                break

            game_state.init(options.diameter, len(players), options.speed)
            options.resolution = pygame.display.get_window_size()
            net.send("start", options.to_json())
            await asyncio.sleep(0.2)

            for snake, func in zip(game_state.players[:local_players_num], control_functions):
                asyncio.create_task(control_snake(func, snake, options.fps))

            apygame.setView(ReadyGoView(game_state,GameView(game_state, options)))
            await apygame.init(fps=options.fps)

            net.send("score", game_state.to_json())
            await asyncio.sleep(0.2)
            show_scores(game_state.scores, players)
            game_state.reset()
            players.clear()
            players.extend([name, str(server_address)] for name in local_players_names)

    finally:
        net.close()




