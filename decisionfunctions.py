import pygame
import apygame
import MyPodSixNet as net

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
    clock = apygame.Clock()
    while snake.alive:
        await clock.tick(fps)
        snake.decision = function()

async def send_decision(conn: net.EndPoint, name, fps, function):
    clock = apygame.Clock()
    while not conn.transport.is_closing():
        await clock.tick(fps)
        conn.send("control", {"name": name, "direction": function()})