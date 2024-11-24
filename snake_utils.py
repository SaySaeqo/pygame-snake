import sys
import pygame
from dto import *
from gameobjects import *
from constants import Color
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

    def __init__(self, game_state: GameState, options: Options):
        self.state = game_state
        self.options = options

    def update(self, delta):
        st = self.state
        options = self.options

        draw_board(self.state)

        for idx, player in st.enumarate_alive_players():
            player.move(options.diameter * st.current_speed * delta, should_walk_weird=(st.weird_walking_event_timer > 0))
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
            apygame.setView(None)

        # update time counter
        st.time_passed += delta
        st.fruit_event_timer += delta
        st.wall_walking_event_timer = max(0, st.wall_walking_event_timer - delta)
        st.weird_walking_event_timer = max(0, st.weird_walking_event_timer - delta)
        st.destroying_event_timer = max(0, st.destroying_event_timer - delta)
        if st.fruit_event_timer > 5:
            st.fruits.append(Fruit.at_random_position(options.diameter / 2))
            st.fruit_event_timer = 0
        if st.time_passed > options.time_limit:
            st.wall_event_timer += delta
            if st.wall_event_timer > (options.time_limit**2) / (st.time_passed**2):
                st.walls += [Wall.at_random_position(options.diameter)]
                st.wall_event_timer = 0

        # something to make it more fun!
        st.current_speed = options.speed + 2 * int(1 + st.time_passed / 10)
        for player in st.alive_players():
            player.rotation_power = options.rotation_power + int(st.time_passed / 10)


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


class ScrollableView(apygame.PyGameView):
        
        SOME_OFFSET = 30
        SCROLL_SPEED = 10
    
        def __init__(self, title: str, scrollable: str, next_view: apygame.PyGameView):
            self.title = text2surface(title, 72)
            self.scrollable = text2surface(scrollable)
            self.next_view = next_view
            self.scroll = 0

        @property
        def visible_height(self):
            return pygame.display.get_surface().get_height() - 3 * self.SOME_OFFSET - self.title.get_height()
    
        def update(self, delta):
            MenuDrawer(self.SOME_OFFSET)\
                .draw_surface(self.title)\
                .add_space(self.SOME_OFFSET)\
                .draw_surface(self.scrollable.subsurface(pygame.Rect(0, self.scroll*self.SCROLL_SPEED, self.scrollable.get_width(), self.visible_height)))
            
            keys = pygame.key.get_pressed()
            if keys[pygame.K_DOWN]:
                self.scroll = min(self.scroll + 1, (self.scrollable.get_height()-self.visible_height)//self.SCROLL_SPEED)
            if keys[pygame.K_UP]:
                self.scroll = max(0, self.scroll - 1)

        def handle_event(self, event):
            super().handle_event(event)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    apygame.setView(self.next_view)