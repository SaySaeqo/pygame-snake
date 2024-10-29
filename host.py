import asyncio
import MyPodSixNet as net
from decisionfunctions import control_snake
from snake_utils import *
import utils
import windowfunctions
import json


class HostNetworkListener(net.NetworkListener):

    def __init__(self, conn, local_players: list, game_state):
        super().__init__(conn)
        self.players = local_players
        self.game_state = game_state

    def send_lobby_data(self):
        asyncio.create_task(self.conn.send_now("lobby", self.players))

    def Network_connected(self, _):
        log().info(f"Connection from {self.conn.address}")

    def Network_join(self, names):
        new_players = [[name, self.conn.address] for name in names]
        self.players.extend(new_players)

    def Network_get_lobby_data(self, _):
        self.send_lobby_data()

    def Network_get_game_data(self, _):
        asyncio.create_task(self.conn.send_now("game", self.game_state.to_json()))

    def Network_control(self, data):
        idx = utils.find_index(self.players, lambda x: x[0] == data["name"] and x[1] == self.conn.address)
        player = self.game_state.players[idx]
        player.decision = data["direction"]
        
async def run_host(local_players_names: list, options: Options, control_functions: list):
    server_address = net.NetworkAddress("localhost", 31426)
    host = f"{utils.get_my_ip()}:{server_address.port}"
    local_players_num = len(local_players_names)
    players = [[name, server_address.to_json()] for name in local_players_names]
    game_state = GameState()

    server = await net.start_server(server_address, lambda conn: HostNetworkListener(conn, players, game_state))
    
    while True:
        should_start = await windowfunctions.network_room(local_players_names, host)

        if not should_start:
            break

        players_playing_num = len(local_players_names)
        game_state.players = initialize_players(options.diameter, players_playing_num)
        await server.send_now("start", options.to_json())

        async with asyncio.TaskGroup() as tg:
            for snake, func in zip(game_state.players[:local_players_num], control_functions):
                tg.create_task(control_snake(func, snake, options.fps))
            tg.create_task(run_game(game_state, options))

        await server.send_now("score", game_state.to_json())

        show_scores(game_state.scores, map(players, lambda x: x[0]))
        game_state.reset()
    
    del server




