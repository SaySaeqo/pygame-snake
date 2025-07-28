import random
import pygame
import constants
from decisionfunctions import Direction
import pygameutils
import math

class Circle(pygame.Vector2):

    def __init__(self, x, y, radius, color=constants.Color.default, outline_width=0):
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
        if pygame.display.get_surface():
            rect = pygame.display.get_surface().get_rect()
        else:
            rect = constants.Game().screen_rect
        x = random.random() * rect.width
        y = random.random() * rect.height
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
    def __init__(self, x, y, radius, powerup = constants.Powerup.NONE):
        self.powerup = powerup
        super().__init__(x, y, radius, powerup.value)

    def respawn(self):
        if pygame.display.get_surface():
            rect = pygame.display.get_surface().get_rect()
        else:
            rect = constants.Game().screen_rect
        self.x = random.random() * rect.width
        self.y = random.random() * rect.height
        rnd = random.random()
        if rnd < 0.1:
            self.powerup = constants.Powerup.WALL_WALKING
        elif rnd < 0.2:
            if self.powerup == constants.Powerup.WALL_WALKING:
                self.powerup = constants.Powerup.CRUSHING
            else:
                self.powerup = constants.Powerup.WEIRD_WALKING
        elif rnd < 0.25:
            self.powerup = constants.Powerup.GHOSTING
        else:
            self.powerup = constants.Powerup.NONE
        self.color = self.powerup.value
        self.surface = pygame.Surface((self.r * 2, self.r * 2), flags=pygame.SRCALPHA)
        pygame.draw.circle(self.surface, self.color, (self.r, self.r), self.r, self.outline_width)

    def to_json(self):
        return super().to_json() | {
            "powerup": self.powerup.name
        }
    
    @classmethod
    def from_json(cls, json):
        return cls(json["x"], json["y"], json["r"], constants.Powerup[json["powerup"]])
                    

class Wall(Circle):
    def __init__(self, x, y, radius, color=constants.Color.blue, outline_width=0):
        super().__init__(x, y, radius, color, outline_width)
        
class Tail(Circle):
    def __init__(self, x, y, radius, direction, color=constants.Color.default, outline_width=0):
        super().__init__(x, y, radius, color, outline_width)
        self.direction: pygame.Vector2 = direction

    def to_json(self):
        return super().to_json() | {
            "direction": {
                "x": self.direction.x,
                "y": self.direction.y
            },
        }
    
    @classmethod
    def from_json(cls, json, color, outline_width):
        return cls(json["x"], json["y"], json["r"], pygame.Vector2(json["direction"]["x"], json["direction"]["y"]), color, outline_width)
    
class Snake(Circle):
    def __init__(self, x, y, radius, color=constants.Color.white, outline_width=0):
        super().__init__(x, y, radius, color, outline_width)
        self.decision = Direction.FORWARD
        self.tail: list[Tail] = []
        self.direction = pygame.Vector2(random.random(), random.random()).normalize()
        self.rotation_power = 5  # distance sin size of snake width in witch snake successfully turns back
        self.alive = True
        self.powerups = {}

    def move(self, distance):
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
                if pygame.display.get_surface():
                    screen_rect = pygame.display.get_surface().get_rect()
                else:
                    screen_rect = constants.Game().screen_rect
                width, height = screen_rect.size

                # Create a list of translations
                translations = [(0, 0), (-width, 0), (width, 0), (0, -height), (0, height), (-width, -height), (-width, height), (width, -height), (width, height)]

                # Apply each translation to the original point
                points = [(x + dx, y + dy) for dx, dy in translations]

                # Find the closest point to the target point
                closest = min(points, key=lambda p: t.distance_to(p))

                if constants.Powerup.WEIRD_WALKING in self.powerups or constants.Powerup.CRUSHING in self.powerups:
                    t.x += self.direction.x * distance
                    t.y += self.direction.y * distance
                else:
                    t.x, t.y = t.move_towards(closest, distance)
                t.direction = (closest - t).normalize() if closest != t else prev.direction

                t.x = (t.x + screen_rect.width) % screen_rect.width
                t.y = (t.y + screen_rect.height) % screen_rect.height


    def consume(self, fruit):
        last = self.tail[-1] if self.tail else self
        new_tail = Tail(last.x, last.y, self.r, last.direction, self.color, outline_width=int(self.r / 2))
        self.tail.append(new_tail)
        if fruit.powerup not in [constants.Powerup.NONE, constants.Powerup.WALL_WALKING]:
            if fruit.powerup in self.powerups:
                self.powerups[fruit.powerup] += constants.POWERUP_TIMES[fruit.powerup]
            else:
                self.powerups[fruit.powerup] = constants.POWERUP_TIMES[fruit.powerup]
        fruit.respawn()
        

    def draw(self):
        if self.powerups:
            self.draw_with_timer()
            return
        super().draw()
        for t in self.tail:
            t.draw()

    def update_timer(self, delta):
        for powerup in list(self.powerups):
            self.powerups[powerup] -= delta
            if self.powerups[powerup] < 0:
                del self.powerups[powerup]

    def draw_with_timer(self):
        for powerup, time in sorted(list(self.powerups.items()), key=lambda x: x[1], reverse=True):
            num_of_segments = len(self.tail) + 1
            segments_to_color = time
            fully_colored = int(math.floor(segments_to_color))
            rest = segments_to_color - fully_colored
            segments = [self] + self.tail
            for segment, percentage in zip(segments, fully_colored * [1] + [rest] + (num_of_segments - fully_colored - 1) * [0]):
                current_sur = segment.surface
                segment.surface = pygameutils.paint_surface(current_sur, powerup.value, percentage, -segment.direction)
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
        if pygame.display.get_surface():
            screen_rect = pygame.display.get_surface().get_rect()
        else:
            screen_rect = constants.Game().screen_rect
        x = random.random() * screen_rect.width * 0.6 + screen_rect.width * 0.2
        y = random.random() * screen_rect.height * 0.6 + screen_rect.height * 0.2
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
            "color": self.color,
            "powerups": {p.name: t for p,t in self.powerups.items()}
        }
     
    @classmethod
    def from_json(cls, json):
        snake = cls(json["x"], json["y"], json["r"], json["color"])
        snake.decision = json["decision"]
        snake.direction = pygame.Vector2(json["direction"]["x"], json["direction"]["y"])
        snake.rotation_power = json["rotation_power"]
        snake.alive = json["alive"]
        for t in json["tail"]:
            tail = Tail.from_json(t, snake.color, outline_width=int(snake.r / 2))
            snake.tail.append(tail)
        for p, t in json["powerups"].items():
            snake.powerups[constants.Powerup[p]] = t
        return snake