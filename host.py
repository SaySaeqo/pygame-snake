import asyncio
import gamenetwork as net
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

    def action_join(self, names):
        new_players = [[name, self.address] for name in names]
        self.players.extend(new_players)

    def action_control(self, data):
        idx = utils.find_index(self.players, lambda x: x[0] == data["name"] and x[1] == self.address)
        player = self.game_state.players[idx]
        player.decision = data["direction"]

    def disconnected(self):
        log().info("Player disconnected")
        for i in range(len(self.players)):
            if self.players[i][1] == self.address:
                del self.players[i]
        
async def run_host(local_players_names: list, control_functions: list):
    server_address = (None, 31426)
    host = f"{utils.get_my_ip()}:{server_address[1]}"
    local_players_num = len(local_players_names)
    players = [[name, server_address] for name in local_players_names]
    game_state = GameState()

    await net.start_server(server_address, lambda address: HostNetworkListener(address, players, game_state))
    
    while True:
        should_start = await windowfunctions.network_room(players, host)
        log().debug("Should start: %s", should_start)

        if not should_start:
            break

        game_state.init(len(players))
        net.send("start", pygame.display.get_window_size())
        await asyncio.sleep(0.2)

        for snake, func in zip(game_state.players[:local_players_num], control_functions):
            asyncio.create_task(control_snake(func, snake))

        await ReadyGoView(game_state,GameView(game_state))

        net.send("score", game_state.to_json())
        await asyncio.sleep(0.2)
        show_scores(game_state.scores, players)
        game_state.reset()
        players.clear()
        players.extend([name, server_address] for name in local_players_names)

    net.close()




