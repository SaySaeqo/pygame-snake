import pygame
import apygame
import gamenetwork as net
import constants

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

async def control_snake(function, snake):
    clock = apygame.AsyncClock()
    while snake.alive:
        await clock.tick(constants.Game.fps)
        snake.decision = function()

async def send_decision(address: tuple[str, int], name, function):
    clock = apygame.AsyncClock()
    while net.is_connected(address):
        await clock.tick(constants.Game.fps)
        net.send("control", {"name": name, "direction": function()}, to=address)