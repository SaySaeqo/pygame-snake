import asyncio
import MyPodSixNet as net
from decisionfunctions import control_snake
from snake_utils import *
import utils
import windowfunctions
import json


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
    server_address = net.NetworkAddress("localhost", 31426)
    host = f"{utils.get_my_ip()}:{server_address.port}"
    local_players_num = len(local_players_names)
    players = [[name, str(server_address)] for name in local_players_names]
    game_state = GameState()

    server = await net.start_server(server_address, lambda conn: HostNetworkListener(conn, players, game_state))

    async def read_data():
        while True:
            await server.pump()
            await asyncio.sleep(0.1)

    read_data_task = asyncio.create_task(read_data())
    
    while True:
        should_start = await windowfunctions.network_room(players, host)
        log().debug("Should start: %s", should_start)

        if not should_start:
            break

        players_playing_num = len(players)
        game_state.players = initialize_players(options.diameter, players_playing_num)
        server.send("start", options.to_json())

        async with asyncio.TaskGroup() as tg:
            for snake, func in zip(game_state.players[:local_players_num], control_functions):
                tg.create_task(control_snake(func, snake, options.fps))
            tg.create_task(run_game(game_state, options))

        server.send("score", game_state.to_json())

        show_scores(game_state.scores, map(lambda x: x[0], players))
        game_state.reset()
    
    read_data_task.cancel()
    del server




