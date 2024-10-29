import pygame
from asyncclock import Clock

class Direction:
    FORWARD = 0
    LEFT = 1
    RIGHT = 2

def based_on_keys(left, right):
    def function():
        keys = pygame.key.get_pressed()
        if keys[left]: return Direction.LEFT
        if keys[right]: return Direction.RIGHT
        return Direction.FORWARD
    return function

async def control_snake(function, snake, fps):
    clock = Clock()
    while snake.alive:
        await clock.tick(fps)
        snake.decision = function()

async def send_decision(conn, name, fps, function):
    clock = Clock()
    while True:
        await clock.tick(fps)
        conn.send("control", {"name": name, "direction": function()})