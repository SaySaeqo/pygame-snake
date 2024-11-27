import pygame
import gamenetwork as net

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