import sys
import pygame
from dto import *
from gameobjects import *
from constants import *
from windowfunctions import *
from dataclasses import dataclass, field
from decisionfunctions import based_on_keys
import apygame
import gamenetwork as net
import logging

def log():
    return logging.getLogger("snake")

def draw_board(state: GameState):
        pygame.display.get_surface().fill(Color.black)
        if not state:
            title("NO GAME STATE\n(error)", offset=10)
            return
        
        # draw game objects
        for player in state.alive_players():
            player.draw()
        for fruit in state.fruits:
            fruit.draw()
        for wall in state.walls:
            wall.draw()

        # draw wall
        if state.wall_walking_event_timer == 0:
            pygame.draw.rect(pygame.display.get_surface(), Color.cyan, pygame.display.get_surface().get_rect(), 1)

        # draw time and score
        time_phrase = "TIME: "
        time_phrase += f"{int(state.time_passed / 60)}:{int(state.time_passed) % 60:02d}" if state.time_passed >= 60 else f"{int(state.time_passed)}"
        score_phrase = f"SCORE: {sum(state.scores)}"
        title(time_phrase + "\n" + score_phrase, offset=10)

        # draw arrows for 1st 2 seconds
        if state.time_passed < 2:
            for player in state.alive_players():
                player.draw_direction()

def show_scores(scores, names):
    end_phrase = "GAME OVER\n"
    end_phrase += f"TOTAL SCORE: {sum(scores)}\n"
    for name, score in zip(names, scores):
        end_phrase += f"{name}: {score}\n"
    pause(end_phrase)

class GameView(apygame.PyGameView):

    def __init__(self, game_state: GameState):
        self.state = game_state

    def update(self, delta):
        st = self.state

        draw_board(self.state)

        for idx, player in st.enumarate_alive_players():
            player.move(Game.diameter * st.current_speed * delta, should_walk_weird=(st.weird_walking_event_timer > 0))
            # region COLLISION_CHECK
            # with fruits
            for fruit in st.fruits:
                if fruit.is_colliding_with(player):
                    if fruit.gives_wall_walking:
                        st.wall_walking_event_timer += 5
                    if fruit.gives_weird_walking:
                        st.weird_walking_event_timer += 15
                    if fruit.gives_wall_walking and fruit.gives_weird_walking:
                        st.destroying_event_timer += 5
                    player.consume(fruit)
                    st.scores[idx] += 1
            # with walls
            for wall in st.walls:
                if wall.is_colliding_with(player):
                    if st.destroying_event_timer > 0:
                        pygame.mixer.Sound("sound/crush.mp3").play(maxtime=1000)
                        st.walls.remove(wall)
                    else:
                        player.died()
                        log().info(f"Player {idx+1} clashed with wall")
            # with borders
            if not pygame.display.get_surface().get_rect().contains(player.get_rect()):
                if (st.wall_walking_event_timer == 0):
                    player.died()
                    log().info(f"Player {idx+1} got out of border")
                else:
                    player.x = (player.x + pygame.display.get_surface().get_rect().width) % pygame.display.get_surface().get_rect().width
                    player.y = (player.y + pygame.display.get_surface().get_rect().height) % pygame.display.get_surface().get_rect().height
            # with tail
            for pl in st.alive_players():
                if player.is_colliding_with(pl):
                    player.died()
                    log().info(f"Player {idx+1} clashed with sb's tail")
            # endregion
        if st.all_players_dead():
            apygame.closeView()

        # update time counter
        st.time_passed += delta
        st.fruit_event_timer += delta
        st.wall_walking_event_timer = max(0, st.wall_walking_event_timer - delta)
        st.weird_walking_event_timer = max(0, st.weird_walking_event_timer - delta)
        st.destroying_event_timer = max(0, st.destroying_event_timer - delta)
        if st.fruit_event_timer > 5:
            st.fruits.append(Fruit.at_random_position(Game.diameter / 2))
            st.fruit_event_timer = 0
        if st.time_passed > Game.time_limit:
            st.wall_event_timer += delta
            if st.wall_event_timer > (Game.time_limit**2) / (st.time_passed**2):
                st.walls += [Wall.at_random_position(Game.diameter)]
                st.wall_event_timer = 0

        # something to make it more fun!
        st.current_speed = Game.speed + 2 * int(1 + st.time_passed / 10)
        for player in st.alive_players():
            player.rotation_power = Game.rotation_power + int(st.time_passed / 10)

        for snake, function in zip(st.players[:Config().number_of_players], Config().control_functions):
            snake.decision = function()


    def handle_event(self, event):
        if event.type == pygame.QUIT:
            sys.exit()
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_p, pygame.K_PAUSE, pygame.K_SPACE):
            pause()
            draw_board(self.state)

    async def do_async(self):
        net.send("game", self.state.to_json())

class ReadyGoView(apygame.PyGameView):

    def __init__(self, game_state: GameState, next_view: apygame.PyGameView):
        self.state = game_state
        self.next_view = next_view
        self.time_passed = 0

    def update(self, delta):
        self.time_passed += delta
        draw_board(self.state)
        if self.time_passed <= 0.666:
            title("READY?", Align.CENTER)
        elif self.time_passed <= 1:
            title("GO!", Align.CENTER, 144)
        else:
            apygame.setView(self.next_view)

    async def do_async(self):
        net.send("game", self.state.to_json())


MENU_OFFSET = 30
def titleMenuDrawer(title: str):
    return MenuDrawer(MENU_OFFSET)\
        .draw(title, 72)\
        .add_space(MENU_OFFSET)

class ScrollableView(apygame.PyGameView):
        
        SCROLL_SPEED = 10
    
        def __init__(self, title: str, scrollable: str):
            self.title = title
            self.scrollable = text2surface(scrollable)
            self.scroll = 0
            self.visible_height = pygame.display.get_surface().get_height() - 3*MENU_OFFSET - text2surface(title, 72).get_height()
    
        def update(self, delta):
            titleMenuDrawer(self.title)\
                .draw_surface(self.scrollable.subsurface(pygame.Rect(
                        0, self.scroll*self.SCROLL_SPEED,
                        self.scrollable.get_width(), self.visible_height
                    )))
            
            keys = pygame.key.get_pressed()
            if keys[pygame.K_DOWN]:
                self.scroll = min(self.scroll + 1, (self.scrollable.get_height()-self.visible_height)//self.SCROLL_SPEED)
            if keys[pygame.K_UP]:
                self.scroll = max(0, self.scroll - 1)

        def handle_event(self, event):
            super().handle_event(event)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    apygame.closeView()

class InputView(apygame.PyGameView):

    MAX_INPUT_LENGTH = 24
    
    def __init__(self, title: str, value: str, character_filter=lambda c: True):
        self.title = title
        self.value = value
        self.character_filter = character_filter

    def update(self, delta):
        titleMenuDrawer(self.title)\
            .draw(self.value)

    def handle_event(self, event):
        super().handle_event(event)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                apygame.closeViewWithResult(self.value)
            elif event.key == pygame.K_ESCAPE:
                apygame.closeView()
            elif event.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]
            elif event.key == pygame.K_DELETE:
                self.value = ""
            elif len(self.value) < self.MAX_INPUT_LENGTH \
                    and event.unicode.isprintable()\
                    and self.character_filter(event.unicode):
                self.value += event.unicode

class KeyInputView(apygame.PyGameView):
    
    def __init__(self, title: str):
        self.title = title

    def update(self, delta):
        titleMenuDrawer(self.title)

    def handle_event(self, event):
        super().handle_event(event)
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                apygame.closeView()
            else:
                apygame.closeViewWithResult(event.key)

class MenuView(apygame.PyGameView):
        
        OPTION_OFFSET = 10
        OUTLINE_WIDTH = 2
    
        def __init__(self, title: str, options: list, choice=0):
            self.title = title
            self.options = options
            self.choice = choice
    
        def update(self, delta):
            drawer = titleMenuDrawer(self.title)
            for idx, option in enumerate(self.options):
                if idx == self.choice:
                    selected = get_with_outline(text2surface(option), self.OUTLINE_WIDTH)
                    drawer.add_space(-self.OUTLINE_WIDTH).draw_surface(selected).add_space(self.OPTION_OFFSET-self.OUTLINE_WIDTH)
                else:
                    drawer.draw(option).add_space(self.OPTION_OFFSET)
            
        def handle_event(self, event):
            super().handle_event(event)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.choice = (self.choice - 1) % len(self.options)
                elif event.key == pygame.K_DOWN:
                    self.choice = (self.choice + 1) % len(self.options)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    apygame.closeViewWithResult(self.choice)
                elif event.key == pygame.K_ESCAPE:
                    apygame.closeView()

class WaitingView(apygame.PyGameView):
    
    def __init__(self, msg: str):
        self.msg = msg
        self.count = 0.0

    def update(self, delta):
        title(self.msg + "."*floor(self.count), Align.CENTER)
        self.count = (self.count + delta) % 4

    def handle_event(self, event):
        super().handle_event(event)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
            apygame.closeView()

class LobbyView(apygame.PyGameView):

    def __init__(self, host, players):
        self.host = host
        self.players = players

    @property
    def players_phrase(self):
        return "\n".join(map(lambda x: str(x),self.players))

    def update(self, delta):
        windowfunctions.MenuDrawer(MENU_OFFSET)\
            .draw("Network Room", 72)\
            .draw("(Press enter to start)", 18)\
            .add_space(MENU_OFFSET)\
            .draw(f"Host: {self.host}", 24)\
            .add_space(MENU_OFFSET*2)\
            .draw(self.players_phrase)
        
    def handle_event(self, event):
        super().handle_event(event)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                apygame.closeViewWithResult(True)
            if event.key == pygame.K_ESCAPE:
                apygame.closeView()

    async def do_async(self):
        net.send("lobby", self.players)