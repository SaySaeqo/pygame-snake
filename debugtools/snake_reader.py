import json
import dto
import views
import pygame
import pygameutils
import sys
from pygameview.utils import title, Align

DEBUG_FPS = 10
GAMESTATES = "debugtools/gamestates.data"
will_pause = False

def draw_debug(game_state: dto.GameState):
    title(
        f"Time: {game_state.time_passed:.2f}\n"
        f"Stamp: ...{game_state.timestamp%1_000_000:.2f}", 
        Align.TOP_LEFT
    )
    title(
        f"Speed: {game_state.current_speed}\n"
        f"WallWlkE: {game_state.wall_walking_event_timer:.2f}\n"
        f"WallE: {game_state.wall_event_timer:.2f}\n"
        f"FruitE: {game_state.fruit_event_timer:.2f}",
        Align.TOP_RIGHT
    )
    title(
        "\n".join(
            f"Pl{i}Pwrs: {",".join(pl.powerups) or "None"}" for i, pl in enumerate(game_state.players)
        ),
        Align.BOTTOM_LEFT
    )
    for player in game_state.alive_players():
        player.draw_direction()

def pause(clock, msg="PAUSED"):
    title(msg, Align.CENTER, 72)
    pygame.display.update()
    while True:
        global will_pause
        clock.tick(DEBUG_FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
                return 0
            if e.type == pygame.KEYDOWN and e.key == pygame.K_j:
                print(game_state.to_json())
            if e.type == pygame.KEYDOWN and e.key == pygame.K_RIGHT:
                will_pause = True
                return 0
            if e.type == pygame.KEYDOWN and e.key == pygame.K_LEFT:
                will_pause = True
                return -2

if __name__ == "__main__":
    pygameutils.create_window("Debug_reader")
    clock = pygame.time.Clock()
    game_states = []
    with open(GAMESTATES) as file:
        game_states = [dto.GameState.from_json(json.loads(line)) for line in file.readlines()]
    i = 0
    while True:
        if will_pause:
            will_pause = False
            if i < len(game_states):
                i += pause(clock)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                i += pause(clock)
        if i == len(game_states):
            i += pause(clock, "RETRY?")
        i %= len(game_states)
        game_state = game_states[i]
        views.draw_board(game_state)
        draw_debug(game_state)
        pygame.display.update()
        clock.tick(DEBUG_FPS)
        i += 1
    



