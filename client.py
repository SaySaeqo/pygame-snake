import gamenetwork as net
import views
from utils import *
from views import *
import pygameview
from dataclasses import dataclass, field
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
import math


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
for filename in filenames:
    if filename == prefix + str(index) + ".data":
        index += 1
DEBUG_FILENAME = f"{debugtools_dir}/{prefix}{index}.data"
print(DEBUG_FILENAME)

def DEBUG_WRITE2FILE(some_json):
    return
    with open(DEBUG_FILENAME, "a") as file:
        file.write(json.dumps(some_json) + "\n")

@singleton
@dataclass
class ClientNetworkData:
    players: list = field(default_factory=list)
    predicted: GameState = None
    my_colors: dict = field(default_factory=dict)
    inputs: list = field(default_factory=list)
    inputs_sended_idx: int = 0

should_relaunch = True

async def send_controls():
    while True:
        if ClientNetworkData().inputs_sended_idx < 0:
            ctrls = []
            for game_input in ClientNetworkData().inputs[ClientNetworkData().inputs_sended_idx:]:
                color, decision, time_passed = game_input
                name = find(ClientNetworkData().my_colors.keys(), lambda n: ClientNetworkData().my_colors[n] == color)
                ctrls.append({"name": name, "direction": decision, "time_passed": time_passed})
            net.send_udp("control", { "ctrls" : ctrls })
            ClientNetworkData().inputs_sended_idx = 0
        await asyncio.sleep(constants.NETWORK_GAME_LATENCY_SEC)


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


class ClientGameView(pygameview.PyGameView):

    def update(self, delta):
        if ClientNetworkData().predicted is None:
            return
        
        for name, function in zip(Config().active_players_names, Config().control_functions):
            if ClientNetworkData().predicted and name in ClientNetworkData().my_colors:
                color = ClientNetworkData().my_colors[name]
                decision = function()
                snake = find(ClientNetworkData().predicted.players, lambda s: s.color == color)
                snake.decision = decision
                loop_delta_fragment = 0.0001
                ClientNetworkData().inputs.append((color, decision, ClientNetworkData().predicted.time_passed - loop_delta_fragment))
                ClientNetworkData().inputs_sended_idx -= 1
                DEBUG_WRITE2FILE({"color": color, "decision": decision, "time_passed": ClientNetworkData().predicted.time_passed})

        sounds = game_loop(ClientNetworkData().predicted, delta, add_new_entities=False)
        draw_board(ClientNetworkData().predicted)
        for sound in sounds:
            pygame.mixer.Sound(f"sound/{sound}.mp3").play(maxtime=constants.SOUND_MAXTIME[sound])

class ClientReadyGoView(views.ReadyGoView):

    def __init__(self, next_view: pygameview.PyGameView):
        super().__init__(ClientNetworkData().predicted, next_view)

    def update(self, delta):
        self.state = ClientNetworkData().predicted
        super().update(delta)

    async def do_async(self):
        pass


class ClientNetworkListener(client_tester.ClientTester):

    def __init__(self):
        super().__init__()
        self.controls_task = None

    def action_lobby(self, players):
        ClientNetworkData().players = players

    def action_game(self, game_state):
        gs = GameState.deserialize(game_state)
        if ClientNetworkData().predicted is not None and ClientNetworkData().predicted.timestamp > gs.timestamp:
            return
        
        # time_of_arrival = 0
        # if ClientNetworkData().predicted is not None:
        #     time_of_arrival = ClientNetworkData().predicted.time_passed

        # debug2file_json = gs.to_json()
        # debug2file_json["time_of_arrival"] = time_of_arrival
        # DEBUG_WRITE2FILE(debug2file_json)

        if ClientNetworkData().predicted is not None and ClientNetworkData().predicted.time_passed > 1:
            current_time = ClientNetworkData().predicted.time_passed - 0.0001
            # now = pygame.time.get_ticks()
            # from_last_msg = (now - self.test) / 1000.0
            # self.test = now
            # if current_time - gs.time_passed > 2 * constants.NETWORK_GAME_LATENCY / 1000:
            #     time_diff = current_time - gs.time_passed
            #     constants.LOG.debug(f"3. {time_diff=:.4f}\t{from_last_msg=:.4f}")
            ClientNetworkData().predicted = gs
            ClientNetworkData().predicted.time_passed = current_time
            delta_time = 1.0 / pygameview.DEFAULT_FPS
            if gs.time_passed < 1.0:
                ClientNetworkData().predicted.time_passed = 1.0
                ClientNetworkData().inputs = [inp for inp in ClientNetworkData().inputs if inp[2] >= 1.0]
            else:
                ClientNetworkData().inputs = [inp for inp in ClientNetworkData().inputs if inp[2] > gs.time_passed - delta_time]
            for color, decision, tp in ClientNetworkData().inputs:
                # If all inputs are processed up to current state, fast-forward in units of delta_time
                if tp > ClientNetworkData().predicted.time_passed:
                    loop_delta = math.ceil((tp - ClientNetworkData().predicted.time_passed)/delta_time)*delta_time
                    game_loop(ClientNetworkData().predicted, loop_delta, False)
                # Else just apply the input
                snake = find(gs.players, lambda s: s.color == color)
                snake.decision = decision
            if current_time > ClientNetworkData().predicted.time_passed:
                loop_delta = math.ceil((current_time - ClientNetworkData().predicted.time_passed)/delta_time)*delta_time
                game_loop(ClientNetworkData().predicted, loop_delta, False)
        else:
            ClientNetworkData().predicted = gs
            delta_time = 1.0 / pygameview.DEFAULT_FPS
            loop_delta = math.ceil((2*constants.NETWORK_GAME_LATENCY_SEC)/delta_time)*delta_time
            ClientNetworkData().predicted.time_passed += loop_delta
            # self.test = pygame.time.get_ticks()


    def action_your_color(self, data):
        color = data["color"]
        name = data["name"]
        ClientNetworkData().my_colors[name] = color

    def action_start(self, resolution):
        constants.LOG.info("Game is starting")
        self.controls_task = asyncio.create_task(send_controls())
        ClientNetworkData().predicted = None
        pygame.display.set_mode(resolution, pygame.FULLSCREEN if resolution == pygameutils.get_screen_size() else 0)
        pygameview.set_view(ClientReadyGoView(ClientGameView()))

    def action_score(self, game_state):
        game_state = GameState.deserialize(game_state)
        self.controls_task.cancel()
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
            await pygameview.wait_closed()
        
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
        session_id = "0c746976-ae9f-11f0-bad9-a6a2e6ca50bc"
        playfab.PlayFabMultiplayerAPI.RequestMultiplayerServer({
                "BuildId": "ba614b2d-bac0-4620-8385-88f3fb4fa604",
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
        print(f"SessionId = {session_id}")
        # ipv4 = "192.168.1.104"
        # tcp_port = 8080
        # udp_port = 8081

        pygameview.close_view()
        await pygameview.wait_closed()
        await run_client(ipv4, tcp_port, udp_port)

        # Printing logs from server
        with net.ContextManager():
            await net.connect_to_server(ipv4, tcp_port, udp_port, ClientNetworkListener())
            net.send("get_logs", "100")
            await asyncio.sleep(1)

        await client_tester.main(ipv4, tcp_port, udp_port)
        
    except PlayfabError as e:
        constants.LOG.error(f"Playfab error: {e}")
    except playfab.PlayFabErrors.PlayFabException as e:
        constants.LOG.error(f"Playfab exception {e}")
    except Exception as e:
        traceback.print_exc()
        constants.LOG.error(f"Unexpected error: {e}")

    pygameview.close_view()

    

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, filemode="w", filename="client.log")
    pygameutils.create_window("Playfab test", (800, 600))
    asyncio.run(run_on_playfab())