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

    try:
        await net.start_server(server_address, lambda address: HostNetworkListener(address, players, game_state))
    except OSError as e:
        constants.LOG.error(f"Could not start the server: {e}")
        net.close()
        return
    
    while True:
        should_start = await LobbyView(host, players)
        if not should_start: break

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

    net.close()




