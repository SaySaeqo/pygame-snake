import random
import pygame
from constants import Color
from decisionfunctions import Direction
import pygameutils
import math

class Circle(pygame.Vector2):

    def __init__(self, x, y, radius, color=Color.default, outline_width=0):
        super().__init__(x, y)
        self.r = radius
        self.outline_width = outline_width
        self.color = color
        self.surface = pygame.Surface((radius * 2, radius * 2), flags=pygame.SRCALPHA)
        pygame.draw.circle(self.surface, color, (radius, radius), radius, outline_width)

    def __str__(self) -> str:
        return self.__class__.__name__ + super().__str__()

    def draw(self):
        pygame.display.get_surface().blit(self.surface, (self.x - self.r, self.y - self.r))

    def is_colliding_with(self, other):
        return other is not self and isinstance(other, Circle) and self.distance_to(other) < self.r + other.r

    @classmethod
    def at_random_position(cls, radius, color=None):
        x = random.random() * pygame.display.get_surface().get_rect().width
        y = random.random() * pygame.display.get_surface().get_rect().height
        return cls(x, y, radius) if not color else cls(x, y, radius, color)

    def get_rect(self):
        return pygame.Rect(self.x - self.r, self.y - self.r, self.r * 2, self.r * 2)

    def __deepcopy__(self, memo):
        """ No copy """
        memo[id(self)] = self
        return self
    
    def to_json(self):
        return {
            "x": self.x,
            "y": self.y,
            "r": self.r
        }
    
    @classmethod
    def from_json(cls, json):
        return cls(json["x"], json["y"], json["r"])


class Fruit(Circle):
    def __init__(self, x, y, radius, gives_wall_walking=False, gives_weird_walking=False):
        self.gives_wall_walking = gives_wall_walking
        self.gives_weird_walking = gives_weird_walking
        super().__init__(x, y, radius, self.calculate_color())

    def calculate_color(self):
        if self.gives_wall_walking and self.gives_weird_walking:
            return Color.gold
        elif self.gives_wall_walking:
            return Color.cyan
        elif self.gives_weird_walking:
            return Color.magenta
        else:
            return Color.green

    def respawn(self):
        self.x = random.random() * pygame.display.get_surface().get_rect().width
        self.y = random.random() * pygame.display.get_surface().get_rect().height
        rnd = random.random()
        if rnd < 0.1:
            self.gives_wall_walking = True
            self.gives_weird_walking = False
        elif rnd < 0.2:
            self.gives_weird_walking = True
            if self.gives_wall_walking:
                pygame.mixer.Sound("sound/bless.mp3").play(maxtime=5000)
        else:
            self.gives_wall_walking = False
            self.gives_weird_walking = False
        self.color = self.calculate_color()
        self.surface = pygame.Surface((self.r * 2, self.r * 2), flags=pygame.SRCALPHA)
        pygame.draw.circle(self.surface, self.color, (self.r, self.r), self.r, self.outline_width)

    def to_json(self):
        return super().to_json() | {
            "gives_wall_walking": self.gives_wall_walking,
            "gives_weird_walking": self.gives_weird_walking
        }
    
    @classmethod
    def from_json(cls, json):
        return cls(json["x"], json["y"], json["r"], json["gives_wall_walking"], json["gives_weird_walking"])
                    

class Wall(Circle):
    def __init__(self, x, y, radius, color=Color.blue, outline_width=0):
        super().__init__(x, y, radius, color, outline_width)
        
class Snake(Circle):
    def __init__(self, x, y, radius, color=Color.white, outline_width=0):
        super().__init__(x, y, radius, color, outline_width)
        self.decision = Direction.FORWARD
        self.tail: list[Circle] = []
        self.direction = pygame.Vector2(random.random(), random.random()).normalize()
        self.rotation_power = 5  # distance sin size of snake width in witch snake successfully turns back
        self.alive = True
        self.timer = 0.0
        self.timer_max = 5.0
        self.timer_color = Color.default

    def move(self, distance, should_walk_weird=False):
        # change direction if key was pressed
        PI = 3.14
        decision = self.decision
        if decision == Direction.LEFT:
            self.direction = self.direction.rotate(-(distance * 180) / (self.rotation_power * self.r * PI))
        elif decision == Direction.RIGHT:
            self.direction = self.direction.rotate((distance * 180) / (self.rotation_power * self.r * PI))

        # move certain distance forward
        self.x += self.direction.x * distance
        self.y += self.direction.y * distance

        for prev, t in zip([self] + self.tail, self.tail):
            if not t.is_colliding_with(prev):

                x, y = prev
                width, height = pygame.display.get_surface().get_rect().size

                # Create a list of translations
                translations = [(0, 0), (-width, 0), (width, 0), (0, -height), (0, height), (-width, -height), (-width, height), (width, -height), (width, height)]

                # Apply each translation to the original point
                points = [(x + dx, y + dy) for dx, dy in translations]

                # Find the closest point to the target point
                closest = min(points, key=lambda p: t.distance_to(p))

                if should_walk_weird:
                    t.x += self.direction.x * distance
                    t.y += self.direction.y * distance
                else:
                    t.x, t.y = t.move_towards(closest, distance)
                t.direction = (closest - t).normalize() if closest != t else prev.direction

                t.x = (t.x + pygame.display.get_surface().get_rect().width) % pygame.display.get_surface().get_rect().width
                t.y = (t.y + pygame.display.get_surface().get_rect().height) % pygame.display.get_surface().get_rect().height


    def consume(self, fruit):
        last = self.tail[-1] if self.tail else self
        new_tail = Circle(last.x, last.y, self.r, self.color, outline_width=int(self.r / 2))
        new_tail.direction = last.direction
        self.tail.append(new_tail)
        # time = 0
        # if fruit.gives_wall_walking:
        #     time = 5
        # elif fruit.gives_weird_walking:
        #     time = 5
        # elif fruit.gives_wall_walking and fruit.gives_weird_walking:
        #     time = 5
        # if time:
        #     self.set_timer(time, fruit.color)
        
        fruit.respawn()
        

    def draw(self):
        if self.timer > 0:
            self.draw_with_timer()
            return
        super().draw()
        for t in self.tail:
            t.draw()

    def set_timer(self, time, color):
        self.timer = time
        self.timer_max = time
        self.timer_color = color

    def update_timer(self, delta):
        self.timer = max(0, self.timer - delta)

    def draw_with_timer(self):
        num_of_segments = len(self.tail) + 1
        segments_to_color = (num_of_segments * self.timer) / self.timer_max
        fully_colored = int(math.floor(segments_to_color))
        rest = segments_to_color - fully_colored
        segments = [self] + self.tail
        for segment, percentage in zip(segments, fully_colored * [1] + [rest] + (num_of_segments - fully_colored - 1) * [0]):
            current_sur = segment.surface
            segment.surface = pygameutils.paint_surface(current_sur, self.timer_color, percentage, -segment.direction)
            if segment is self:
                super().draw()
            else:
                segment.draw()
            segment.surface = current_sur


    def draw_direction(self):
        WIDTH = int(self.r / 4)
        start_point = self + self.direction * self.r * 2
        end_point = start_point + self.direction * self.r * 2
        right_arrow = end_point + self.direction.rotate(150) * self.r
        left_arrow = end_point + self.direction.rotate(-150) * self.r
        pygame.draw.line(pygame.display.get_surface(), self.color, start_point, end_point, WIDTH)
        pygame.draw.line(pygame.display.get_surface(), self.color, end_point, right_arrow, WIDTH)
        pygame.draw.line(pygame.display.get_surface(), self.color, end_point, left_arrow, WIDTH)

    def length(self):
        return len(self.tail) + 1

    def is_colliding_with(self, other):
        if isinstance(other, Snake):
            return super().is_colliding_with(other) or any(self.is_colliding_with(t) for t in other.tail)
        if other in self.tail[:3]: 
            return False
        return super().is_colliding_with(other)
    
    def died(self):
        self.alive = False

    def controls(self, function):
        self.get_decision = function
        return self
    
    @classmethod
    def at_random_position(cls, radius, color=None):
        x = random.random() * pygame.display.get_surface().get_rect().width * 0.6 + pygame.display.get_surface().get_rect().width * 0.2
        y = random.random() * pygame.display.get_surface().get_rect().height * 0.6 + pygame.display.get_surface().get_rect().height * 0.2
        return cls(x, y, radius) if not color else cls(x, y, radius, color)
    
    def to_json(self):
        return super().to_json() | {
            "decision": self.decision,
            "direction": {
                "x": self.direction.x,
                "y": self.direction.y
            },
            "rotation_power": self.rotation_power,
            "alive": self.alive,
            "tail": [t.to_json() for t in self.tail],
            "color": self.color
        }
     
    @classmethod
    def from_json(cls, json):
        snake = cls(json["x"], json["y"], json["r"], json["color"])
        snake.decision = json["decision"]
        snake.direction = pygame.Vector2(json["direction"]["x"], json["direction"]["y"])
        snake.rotation_power = json["rotation_power"]
        snake.alive = json["alive"]
        for t in json["tail"]:
            tail = Circle(t["x"], t["y"], t["r"], snake.color, outline_width=int(snake.r / 2))
            snake.tail.append(tail)
        return snake