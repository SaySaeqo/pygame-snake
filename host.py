import asyncio
import MyPodSixNet as net
from decisionfunctions import control_snake
from snake_utils import *
import utils
import windowfunctions
import apygame


class HostNetworkListener(net.NetworkListener):

    def __init__(self, conn, local_players: list, game_state: GameState):
        super().__init__(conn)
        self.players = local_players
        self.game_state = game_state

    def Network_join(self, names):
        new_players = [[name, str(self.conn.address)] for name in names]
        self.players.extend(new_players)

    def Network_get_lobby_data(self, _):
        self.conn.send("lobby", self.players)

    def Network_get_game_data(self, _):
        self.conn.send("game", self.game_state.to_json())

    def Network_control(self, data):
        idx = utils.find_index(self.players, lambda x: x[0] == data["name"] and x[1] == str(self.conn.address))
        player = self.game_state.players[idx]
        player.decision = data["direction"]
        
async def run_host(local_players_names: list, options: Options, control_functions: list):
    server_address = net.NetworkAddress(None, 31426)
    host = f"{utils.get_my_ip()}:{server_address.port}"
    local_players_num = len(local_players_names)
    players = [[name, str(server_address)] for name in local_players_names]
    game_state = GameState()

    await net.start_server(server_address, lambda conn: HostNetworkListener(conn, players, game_state))
    
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

        apygame.setView(GameView(game_state, options))
        await apygame.init(fps=options.fps)

        net.send("score", game_state.to_json())
        await asyncio.sleep(0.2)
        show_scores(game_state.scores, players)
        game_state.reset()

    net.close()




