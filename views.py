import sys
import pygame
import dto
import gameobjects
import constants
import gamenetwork as net
import pygameview

def draw_board(state: dto.GameState):
        pygame.display.get_surface().fill(constants.Color.black)
        if not state:
            pygameview.utils.title("NO GAME STATE\n(error)", offset=10)
            return
        
        # draw game objects
        for player in state.alive_players():
            player.draw()
        for fruit in state.fruits:
            fruit.draw()
        for wall in state.walls:
            wall.draw()

        # draw wall
        WALL_WIDTH = 2
        FLICKERING_TIME = 2
        FLICKERING_FREQUENCY = 2
        if state.wall_walking_event_timer == 0:
            pygame.draw.rect(pygame.display.get_surface(), constants.Color.cyan, pygame.display.get_surface().get_rect(), WALL_WIDTH)
        elif state.wall_walking_event_timer <FLICKERING_TIME and state.wall_walking_event_timer % (1/FLICKERING_FREQUENCY) < 1/FLICKERING_FREQUENCY/2:
            pygame.draw.rect(pygame.display.get_surface(), constants.Color.cyan, pygame.display.get_surface().get_rect(), WALL_WIDTH)

        # draw time and score
        time_phrase = "TIME: "
        time_phrase += f"{int(state.time_passed / 60)}:{int(state.time_passed) % 60:02d}" if state.time_passed >= 60 else f"{int(state.time_passed)}"
        score_phrase = f"SCORE: {sum(state.scores)}"
        pygameview.utils.title(time_phrase + "\n" + score_phrase, offset=10)

        # draw arrows for 1st 2 seconds
        if state.time_passed < 2:
            for player in state.alive_players():
                player.draw_direction()

def show_scores(scores, names) -> pygameview.common.PauseView:
    end_phrase = "GAME OVER\n"
    end_phrase += f"TOTAL SCORE: {sum(scores)}\n"
    for name, score in zip(names, scores):
        end_phrase += f"{name}: {score}\n"
    return pygameview.common.PauseView(end_phrase)

class GameView(pygameview.PyGameView):

    def __init__(self, game_state: dto.GameState):
        self.state = game_state

    def update(self, delta):
        st = self.state

        draw_board(self.state)

        for idx, player in st.enumarate_alive_players():
            player.move(constants.Game().diameter * st.current_speed * delta)
            # region COLLISION_CHECK
            # with fruits
            for fruit in st.fruits:
                if fruit.is_colliding_with(player):
                    if fruit.powerup == constants.Powerup.WALL_WALKING:
                        st.wall_walking_event_timer += constants.POWERUP_TIMES[constants.Powerup.WALL_WALKING]
                    if fruit.powerup == constants.Powerup.CRUSHING:
                        st.wall_walking_event_timer += constants.POWERUP_TIMES[constants.Powerup.CRUSHING]
                    player.consume(fruit)
                    st.scores[idx] += 1
            # with walls
            for wall in st.walls:
                if wall.is_colliding_with(player):
                    if constants.Powerup.CRUSHING in player.powerups:
                        pygame.mixer.Sound("sound/crush.mp3").play(maxtime=1000)
                        st.walls.remove(wall)
                    elif constants.Powerup.GHOSTING not in player.powerups:
                        player.died()
                        constants.LOG.info(f"Player {idx+1} clashed with wall")
            # with borders
            if not pygame.display.get_surface().get_rect().contains(player.get_rect()):
                if st.wall_walking_event_timer == 0 and constants.Powerup.GHOSTING not in player.powerups:
                    player.died()
                    constants.LOG.info(f"Player {idx+1} got out of border")
                else:
                    player.x = (player.x + pygame.display.get_surface().get_rect().width) % pygame.display.get_surface().get_rect().width
                    player.y = (player.y + pygame.display.get_surface().get_rect().height) % pygame.display.get_surface().get_rect().height
            # with tail
            for pl in st.alive_players():
                if player.is_colliding_with(pl) and not (constants.Powerup.GHOSTING in player.powerups or constants.Powerup.GHOSTING in pl.powerups):
                    player.died()
                    constants.LOG.info(f"Player {idx+1} clashed with sb's tail")
            # endregion
        if st.all_players_dead():
            pygameview.close_view()

        # update time counter
        for player in st.alive_players():
            player.update_timer(delta)
        st.time_passed += delta
        st.fruit_event_timer += delta
        st.wall_walking_event_timer = max(0, st.wall_walking_event_timer - delta)
        if st.fruit_event_timer > 5:
            st.fruits.append(gameobjects.Fruit.at_random_position(constants.Game().diameter / 2))
            st.fruit_event_timer = 0
        if constants.Game().time_limit and st.time_passed > constants.Game().time_limit:
            st.wall_event_timer += delta
            if st.wall_event_timer > (constants.Game().time_limit**2) / (st.time_passed**2):
                st.walls += [gameobjects.Wall.at_random_position(constants.Game().diameter)]
                st.wall_event_timer = 0

        # something to make it more fun!
        st.current_speed = constants.Game().speed + 2 * int(1 + st.time_passed / 10)
        for player in st.alive_players():
            player.rotation_power = constants.Game().rotation_power + int(st.time_passed / 10)

        for snake, function in zip(st.players[:dto.Config().number_of_players], dto.Config().control_functions):
            snake.decision = function()


    def handle_event(self, event):
        if event.type == pygame.QUIT:
            sys.exit()
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_p, pygame.K_PAUSE, pygame.K_SPACE):
            pygameview.set_view(pygameview.common.PauseView("PAUSED", self))

    async def do_async(self):
        net.send_udp("game", self.state.to_json())

class ReadyGoView(pygameview.PyGameView):

    def __init__(self, game_state: dto.GameState, next_view: pygameview.PyGameView):
        self.state = game_state
        self.next_view = next_view
        self.time_passed = 0

    def update(self, delta):
        self.time_passed += delta
        draw_board(self.state)
        if self.time_passed <= 0.666:
            pygameview.utils.title("READY?", pygameview.utils.Align.CENTER)
        elif self.time_passed <= 1:
            pygameview.utils.title("GO!", pygameview.utils.Align.CENTER, 144)
        else:
            pygameview.set_view(self.next_view)

    async def do_async(self):
        net.send_udp("game", self.state.to_json())

class LobbyView(pygameview.PyGameView):

    def __init__(self, host, players):
        self.host = host
        self.players = players

    @property
    def players_phrase(self):
        return "\n".join(map(lambda x: str(x),self.players))

    def update(self, delta):
        pygameview.utils.MenuDrawer(pygameview.common.MENU_LINE_SPACING)\
            .draw("Network Room", 72)\
            .draw("(Press enter to start)", 18)\
            .add_space(pygameview.common.MENU_LINE_SPACING)\
            .draw(f"Host: {self.host}", 24)\
            .add_space(pygameview.common.MENU_LINE_SPACING*2)\
            .draw(self.players_phrase)
        
    def handle_event(self, event):
        super().handle_event(event)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                pygameview.close_view_with_result(True)
            if event.key == pygame.K_ESCAPE:
                pygameview.close_view()

    async def do_async(self):
        net.send_udp("lobby", self.players)