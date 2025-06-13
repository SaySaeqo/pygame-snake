import gamenetwork as net
import views
from utils import *
from views import *
import pygameview
from dataclasses import dataclass
from dto import Config, GameState
import constants
import pygameutils
import playfab
import logging
import traceback

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
                # net.send("start", pygame.display.get_window_size())
                net.send_udp("respond", "HAHA")
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

    def action_print(self, msg):
        constants.LOG.info(msg)


async def run_client(ip:str, tcp_port: int, udp_port: int):
    with net.ContextManager():
        try:
            await first_completed(
                net.connect_to_server(ip, tcp_port, udp_port, lambda address: ClientNetworkListener(address)),
                pygameview.run_async(pygameview.common.WaitingView("Connecting to server"))
                )
        except OSError as e:
            constants.LOG.warning("Could not connect to the server: {}".format(e))
            return
        finally:
            pygameview.close_view()
        
        if not net.is_connected(host_address):
            constants.LOG.info("Connection aborted")
            return
        
        Config().last_connected_ip = f"{ip}:{tcp_port}" 
        Config().save_to_file()

        global should_relaunch
        should_relaunch = True
        while should_relaunch:
            should_relaunch = False
            net.send("join", Config().active_players_names)
            await ClientLobbyView(f"{ip}:{tcp_port}")
    

playfab_result = None

class PlayfabError(Exception): ...

def get_playfab_result(result, error):
    if error:
        raise PlayfabError(error)
    else:
        global playfab_result
        playfab_result = result

def raise_error(e):
    raise e

async def run_on_playfab():

    task = asyncio.create_task(pygameview.run_async(pygameview.common.WaitingView("Connecting to PlayFab")))
    await asyncio.sleep(0)
    global playfab_result
    try:
        playfab.PlayFabSettings.TitleId = "EE89E"
        playfab.PlayFabSettings.GlobalExceptionLogger = raise_error
        playfab.PlayFabClientAPI.LoginWithCustomID({
                "CreateAccount": True,
                "CustomId": "test",
            }, get_playfab_result)
        await asyncio.sleep(0)
        # playfab.PlayFabMultiplayerAPI.RequestMultiplayerServer({
        #         "BuildId": "0eb55df1-2af8-47f7-ba4b-e4b4a4d96bda",
        #         "PreferredRegions": ["NorthEurope"],
        #         "SessionId": "1531a801-9ec3-4d4f-af2f-6d1f3400f9a5",
        #     }, get_playfab_result)
        await asyncio.sleep(0)
        # ports = playfab_result["Ports"]
        # ipv4 = playfab_result["IPV4Address"]
        ipv4 = "20.166.14.209"
        # tcp_port = None
        # udp_port = None
        tcp_port = 30000
        udp_port = 30100
        # for port in ports:
        #     if port["Protocol"] == "TCP":
        #         tcp_port = int(port["Num"])
        #     else:
        #         udp_port = int(port["Num"])
        constants.LOG.info(f"TCP = {tcp_port}\tUDP = {udp_port}\tIPv4 = {ipv4}")
        
        pygameview.close_view()
        await run_client(ipv4, tcp_port, udp_port)
        
    except PlayfabError as e:
        constants.LOG.error(f"Playfab error: {e}")
    except playfab.PlayFabErrors.PlayFabException as e:
        constants.LOG.error(f"Playfab exception {e}")
    except Exception as e:
        traceback.print_exc()
        constants.LOG.error(f"Unexpected error: {e}")

    pygameview.close_view()

    

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    pygameutils.create_window("Playfab test", (800, 600))
    asyncio.run(run_on_playfab())