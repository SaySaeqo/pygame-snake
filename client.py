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
import uuid
import gamenetwork.client_tester as client_tester
import json
import os


# find free data filename
debugtools_dir = "./debugtools"
prefix = "gamestates_"
index = 0
def sk(x:str):
    if not x.startswith(prefix):
        return -1
    nr = int(x.removeprefix(prefix).removesuffix(".data"))
    return nr
filenames = sorted(os.listdir(debugtools_dir), key=sk)
print(filenames)
for filename in filenames:
    if filename == prefix + str(index) + ".data":
        index += 1
DEBUG_FILENAME = f"{debugtools_dir}/{prefix}{index}.data"
print(DEBUG_FILENAME)

def DEBUG_WRITE2FILE(some_json):
    with open(DEBUG_FILENAME, "a") as file:
        file.write(json.dumps(some_json) + "\n")

@singleton
@dataclass
class ClientNetworkData:
    players = []
    game_state: GameState = None
    changed = False
    my_colors = {}

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
                net.send("start", pygame.display.get_window_size())
        super().handle_event(event)


class ClientGameView(views.GameView):

    def __init__(self):
        self.timer = 0
        self.last_timestamp = 0
        self.decisions = []
        self.decisions2 = []

    def update(self, delta):
        if ClientNetworkData().game_state is None:
            return
        # if self.last_timestamp < ClientNetworkData().game_state.timestamp:
        #     self.last_timestamp = ClientNetworkData().game_state.timestamp
        if ClientNetworkData().changed:
            self.state = ClientNetworkData().game_state
            ClientNetworkData().changed = False
            for name in Config().active_players_names:
                color, decision = self.decisions2.pop(0) if self.decisions2 else (ClientNetworkData().my_colors[name], 0)
                find(self.state.players, lambda s: s.color == color).decision = decision
            game_loop(self.state, constants.NETWORK_GAME_LATENCY / 1000)
            self.decisions2 = self.decisions
            self.decisions.clear()
        self.timer += delta
        sounds = game_loop(self.state, delta)

        draw_board(self.state)
        for sound in sounds:
            pygame.mixer.Sound(f"sound/{sound}.mp3").play(maxtime=constants.SOUND_MAXTIME[sound])
        # views.draw_board(self.state)

    async def do_async(self):
        if self.timer > constants.NETWORK_GAME_LATENCY / 1000:
            for name, function in zip(Config().active_players_names, Config().control_functions):
                if ClientNetworkData().game_state and name in ClientNetworkData().my_colors:
                    color = ClientNetworkData().my_colors[name]
                    snake = find(self.state.players, lambda s: s.color == color)
                    snake.decision = self.decisions2.pop(0)[1] if self.decisions2 else 0
                    decision = function()
                    self.decisions.append((color, decision))

                    net.send_udp("control", {"name": name, "direction": decision})
            self.timer = 0

class ClientReadyGoView(views.ReadyGoView):

    def __init__(self, next_view: pygameview.PyGameView):
        super().__init__(ClientNetworkData().game_state, next_view)

    def update(self, delta):
        self.state = ClientNetworkData().game_state
        super().update(delta)

    async def do_async(self):
        pass


class ClientNetworkListener(client_tester.ClientTester):

    def action_lobby(self, players):
        ClientNetworkData().players = players

    def action_game(self, game_state):
        gs = GameState.deserialize(game_state)
        DEBUG_WRITE2FILE(gs.to_json())
        if ClientNetworkData().game_state is not None and ClientNetworkData().game_state.timestamp > gs.timestamp:
            return
        if gs.players[0].alive == False and ClientNetworkData().game_state is not None and ClientNetworkData().game_state.players[0].alive:
            constants.LOG.debug(f"Game state before death: {ClientNetworkData().game_state.to_json()}")
        ClientNetworkData().game_state = gs
        ClientNetworkData().changed = True

    def action_your_color(self, data):
        color = data["color"]
        name = data["name"]
        ClientNetworkData().my_colors[name] = color

    def action_start(self, resolution):
        constants.LOG.info("Game is starting")
        pygame.display.set_mode(resolution, pygame.FULLSCREEN if resolution == pygameutils.get_screen_size() else 0)
        pygameview.set_view(ClientReadyGoView(ClientGameView()))

    def action_score(self, game_state):
        game_state = GameState.deserialize(game_state)
        DEBUG_WRITE2FILE(game_state.to_json())
        constants.LOG.debug(f"Gamestate before scoring: {ClientNetworkData().game_state.to_json()}")
        constants.LOG.debug(f"Game state after scoring: {game_state.to_json()}")
        constants.LOG.info("Game over")
        pygameview.set_view(show_scores(game_state.scores, ClientNetworkData().players))
        global should_relaunch
        should_relaunch = True
        
    def disconnected(self):
        constants.LOG.info("Disconnected from the server")
        pygameview.close_view()


async def run_client(ip:str, tcp_port: int, udp_port: int):
    with net.ContextManager():
        try:
            await first_completed(
                net.connect_to_server(ip, tcp_port, udp_port, ClientNetworkListener()),
                pygameview.run_async(pygameview.common.WaitingView("Connecting to server"))
                )
        except OSError as e:
            constants.LOG.warning("Could not connect to the server: {}".format(e))
            return
        finally:
            pygameview.close_view()
        
        if len(net.tcp_connections) == 0:
            constants.LOG.info("Connection aborted")
            return
        
        Config().last_connected_ip = f"{ip}:{tcp_port}" 
        Config().save_to_file()

        global should_relaunch
        should_relaunch = True
        while should_relaunch:
            should_relaunch = False
            net.send("join", Config().active_players_names)
            await ClientLobbyView(f"{ip}:{tcp_port}:{udp_port}")
    

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
        session_id = str(uuid.uuid1())
        # session_id = "18fe204e-6c8f-11f0-8c9d-a6a2e6ca50bc"
        playfab.PlayFabMultiplayerAPI.RequestMultiplayerServer({
                "BuildId": "840d82de-0543-442a-a019-0afdb8e75666",
                "PreferredRegions": ["NorthEurope"],
                "SessionId": session_id,
            }, get_playfab_result)
        await asyncio.sleep(1)
        ports = playfab_result["Ports"]
        ipv4 = playfab_result["IPV4Address"]
        tcp_port = None
        udp_port = None
        for port in ports:
            if port["Protocol"] == "TCP":
                tcp_port = int(port["Num"])
            else:
                udp_port = int(port["Num"])
        constants.LOG.info(f"TCP = {tcp_port}\tUDP = {udp_port}\tIPv4 = {ipv4}\tSessionId = {session_id}")
        # ipv4 = "192.168.1.104"
        # tcp_port = 8080
        # udp_port = 8081

        pygameview.close_view()
        await run_client(ipv4, tcp_port, udp_port)

        with net.ContextManager():
            await net.connect_to_server(ipv4, tcp_port, udp_port, ClientNetworkListener())
            net.send("get_logs", "100")
            await asyncio.sleep(1)

        # await client_tester.main(ipv4, tcp_port, udp_port)
        
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