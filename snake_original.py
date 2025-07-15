"""
This project's first prototype created within first 24h after it started. Only 1 file, only non-builtin lib is pygame. I am leaving it here for memorial purposes.
PS. The most work done after that was about networking sadly. :(
"""

import random
import sys

import pygame

red = (255, 0, 0)
black = (0, 0, 0)
green = (0, 255, 0)
white = (255, 255, 255)
yellowish = (180, 15, 198)

default_colour = yellowish

CENTER = 1
TOP = 2
BOTTOM = 3

FORWARD = 0
LEFT = 1
RIGHT = 2


class Circle(pygame.Vector2):
    def __init__(self, x, y, radius):
        super().__init__(x, y)
        self.r = radius
        self.colour = default_colour

    def draw(self):
        pygame.draw.circle(pygame.display.get_surface(), self.colour, self, self.r, )

    def is_colliding_with(self, other):
        if other is None: return False
        return self.distance_to(other) < self.r + other.r

    @classmethod
    def at_random_position(cls, radius):
        x = random.random() * pygame.display.get_surface().get_rect().width
        y = random.random() * pygame.display.get_surface().get_rect().height
        return cls(x, y, radius)

    def get_rect(self):
        return pygame.Rect(self.x - self.r, self.y - self.r, self.r * 2, self.r * 2)


class Fruit(Circle):
    def __init__(self, x, y, radius):
        super().__init__(x, y, radius)
        self.colour = green

    def respawn(self):
        self.x = random.random() * pygame.display.get_surface().get_rect().width
        self.y = random.random() * pygame.display.get_surface().get_rect().height


class SnakeTail(Circle):
    def __init__(self, x, y, radius, head):
        super().__init__(x, y, radius)
        self.colour = white
        self.head = head
        self.tail = None

    def draw(self):
        OUTLINE = int(self.r / 2)
        pygame.draw.circle(pygame.display.get_surface(), self.colour, self, self.r, OUTLINE)
        if self.tail:
            self.tail.draw()

    def append_tail(self):
        if self.tail:
            self.tail.append_tail()
        else:
            self.tail = SnakeTail(self.x, self.y, self.r, self)

    def move(self, distance):
        if not self.is_colliding_with(self.head):
            new_position = self.move_towards(self.head, distance)
            self.x = new_position.x
            self.y = new_position.y
            if self.tail:
                self.tail.move(distance)

def get_decision():
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        return LEFT
    elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        return RIGHT

class Snake(Circle):
    def __init__(self, x, y, radius, decision_function=get_decision):
        super().__init__(x, y, radius)
        self.get_decision = decision_function
        self.colour = white
        self.tail = None
        self.direction = pygame.Vector2(random.random(), random.random()).normalize()
        self.rotation_power = 5  # distance in size of snake width in witch snake successfully turns back

    def move(self, distance):
        # change direction if key was pressed
        PI = 3.14
        decision = self.get_decision()
        if decision == LEFT:
            self.direction = self.direction.rotate(-(distance * 180) / (self.rotation_power * self.r * PI))
        elif decision == RIGHT:
            self.direction = self.direction.rotate((distance * 180) / (self.rotation_power * self.r * PI))


        # move certain distance forward
        if self.tail:
            self.tail.move(distance)
        self.x += self.direction.x * distance
        self.y += self.direction.y * distance
        # if self.x > pygame.display.get_surface().get_rect().width:
        #     self.x -= pygame.display.get_surface().get_rect().width
        # elif self.x < 0:
        #     self.x += pygame.display.get_surface().get_rect().width
        # if self.y > pygame.display.get_surface().get_rect().height:
        #     self.y -= pygame.display.get_surface().get_rect().height
        # elif self.y < 0:
        #     self.y += pygame.display.get_surface().get_rect().height

    def consume(self, fruit):
        fruit.respawn()
        if self.tail:
            self.tail.append_tail()
        else:
            self.tail = SnakeTail(self.x, self.y, self.r, self)

    def draw(self):
        super().draw()
        if self.tail:
            self.tail.draw()

    def length(self):
        tail = self.tail
        count = 0
        while tail != None:
            count += 1
            tail = tail.tail
        return count

    def is_colliding_with(self, other):
        if not isinstance(other, Snake):
            return super().is_colliding_with(other)
        if other is not self:
            if self.is_colliding_with(other.tail):
                return True
        if other.tail:
            tail = other.tail.tail
            while tail is not None:
                if self.is_colliding_with(tail):
                    return True
                tail = tail.tail
        return False



class SnakeGame:

    def __init__(self, size: tuple[int, int] = (480, 320), fps: int = 60, diameter: int = 10, speed: int = 8,
                 time_limit: int = 60):
        """
        :param size: width and hight of window in pixels
        :param diameter: size of things in pixels
        :param speed: diameters per second
        :param time_limit: seconds
        """
        pygame.init()
        self.board = pygame.display.set_mode(size)
        pygame.display.set_caption("Snake")
        self.font = pygame.font.SysFont("monospace", 32, bold=True)
        self.clock = pygame.time.Clock()
        self.FPS = fps
        self.SIZE = diameter  # in pixels for diameter length
        self.SPEED = speed  # in size of snake width per second
        self.LINE_SPACING = 10  # distance between lines for displayed text (in pixels)
        self.TIME_LIMIT = time_limit  # in seconds

    def title(self, text: str, align=TOP):
        # chopping line of text into separate surfaces
        lines = (t for t in text.split("\n"))
        text_surfaces = [self.font.render(line, True, white) for line in lines]

        # combining into 1 surface (align: horizontally centered)
        main_surface = pygame.Surface((
            max(t.get_rect().width for t in text_surfaces),
            sum(t.get_rect().height for t in text_surfaces) + self.LINE_SPACING * len(text_surfaces)
        ), flags=pygame.SRCALPHA)
        y = 0
        for sur in text_surfaces:
            main_surface.blit(sur, (main_surface.get_rect().centerx - sur.get_rect().centerx, y))
            y += sur.get_height() + self.LINE_SPACING

        # merging into board (align: horizontally centered; vertically as desired)
        x = pygame.display.get_surface().get_rect().centerx - main_surface.get_rect().centerx
        if align == TOP:
            y = self.LINE_SPACING
        elif align == CENTER:
            y = pygame.display.get_surface().get_rect().centery - main_surface.get_rect().centery
        elif align == BOTTOM:
            y = pygame.display.get_surface().get_height() - main_surface.get_height()
        else:
            raise RuntimeError("Align parameter is not correct")
        pygame.display.get_surface().blit(main_surface, (x, y))

    def pause_with_message(self, message):
        self.title(message, CENTER)
        pygame.display.flip()

        paused = True
        while paused:
            pygame.time.wait(333)
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN and \
                        event.key in (pygame.K_p, pygame.K_PAUSE, pygame.K_SPACE, pygame.K_ESCAPE):
                    paused = False
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    pygame.quit()
                    sys.exit()

    def running(self):
        # initialize game objects
        fruits = [Fruit.at_random_position(self.SIZE / 2) for _ in range(6)]
        def based_on_arrows():
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]: return LEFT
            if keys[pygame.K_RIGHT]: return RIGHT
            return FORWARD
        def based_on_wsad():
            keys = pygame.key.get_pressed()
            if keys[pygame.K_a]: return LEFT
            if keys[pygame.K_d]: return RIGHT
            return FORWARD
        players = [Snake.at_random_position(self.SIZE / 2) for _ in range(1)]
        players[0].get_decision = based_on_arrows
        #players[1].get_decision = based_on_wsad
        def draw_board():
            pygame.display.get_surface().fill(black)
            for player in players:
                player.draw()
            for fruit in fruits:
                fruit.draw()

        draw_board()
        # region READY?
        self.title("READY?", CENTER)
        pygame.display.update()
        ready = False
        while not ready:
            pygame.time.wait(333)
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    ready = True
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    pygame.quit()
                    sys.exit()
        draw_board()
        # endregion
        # region GO!
        tmp = self.font
        self.font = pygame.font.SysFont("monospace", 72, bold=True)
        self.title("GO!", CENTER)
        self.font = tmp
        pygame.display.update()
        pygame.time.wait(333)
        draw_board()
        # endregion

        # inner main loop
        time_passed = 0
        frames_passed = 0
        current_speed = self.SPEED
        score = 0
        while True:
            # displaying view
            draw_board()
            self.title(f"{int(time_passed / 60)}:{time_passed % 60:02d}" if time_passed >= 60 else f"{time_passed}")
            pygame.display.update()

            # pygame "must-have" + pausing
            self.clock.tick(self.FPS)
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.KEYDOWN and \
                        event.key in (pygame.K_p, pygame.K_PAUSE, pygame.K_SPACE):
                    self.pause_with_message("PAUSED")
                    draw_board()
                elif event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            for player in players:
                player.move(self.SIZE * current_speed / self.FPS)
                # region COLLISION_CHECK
                # with fruits
                for fruit in fruits:
                    if fruit.is_colliding_with(player):
                        player.consume(fruit)
                # with borders
                if not pygame.display.get_surface().get_rect().contains(player.get_rect()):
                    score += player.length()
                    players.remove(player)
                    print("Out of border")
                # with tail
                for pl in players:
                    if player.is_colliding_with(pl):
                        score += player.length()
                        players.remove(player)
                        print("Clash with tail")
                # endregion
            if len(players) == 0:
                return score

            # update time counter
            frames_passed = (frames_passed + 1) % self.FPS
            if frames_passed == 0:
                time_passed += 1
            if time_passed > self.TIME_LIMIT:
                return score + sum(player.length() for player in players)

            # something to make it more fun!
            current_speed = self.SPEED + 2 * int(1 + time_passed / 10)
            for player in players:
                player.rotation_power = 5 + int(time_passed / 10)


if __name__ == "__main__":
    game = SnakeGame()
    # main loop
    while True:
        score = game.running()
        game.pause_with_message(f"GAME OVER\nSCORE: {score}")
