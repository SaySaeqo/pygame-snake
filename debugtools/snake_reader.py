# run as module, use: python -m debugtools.snake_reader

import json
import dto
import views
import pygame
import pygameutils
import sys
from pygameview.utils import title, Align

DEBUG_FPS = 10
GAMESTATES = "debugtools/gamestates_11.data"
will_pause = False
CRIMSON_RED = (153, 0, 0)

def create_x_surface(size, color=(255, 0, 0), thickness=5):
    """Create a square pygame.Surface with an 'X' drawn on it."""
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.line(surface, color, (0, 0), (size-1, size-1), thickness)
    pygame.draw.line(surface, color, (0, size-1), (size-1, 0), thickness)
    return surface

def draw_debug(game_state: dto.GameState):
    for player in game_state.alive_players():
        player.draw_direction()
    for player in game_state.players:
        if player.alive is False:
            player.draw()
            player.draw_direction()
            surface = create_x_surface(player.r*3, CRIMSON_RED, int(player.r))
            pygame.display.get_surface().blit(surface, (player.x - player.r*1.5, player.y - player.r*1.5 ))
    title(
        f"Time: {game_state.time_passed:.2f}\n"
        f"Stamp: ...{game_state.timestamp%1_000_000:.2f}\n"
        f"LastD: {game_state.last_delta:.2f}\n"
        f"Nr: {game_state.numbering}", 
        Align.TOP_LEFT
    )
    title(
        f"Speed: {game_state.current_speed}\n"
        f"WallWlkE: {game_state.wall_walking_event_timer:.2f}\n"
        f"WallE: {game_state.wall_event_timer:.2f}\n"
        f"FruitE: {game_state.fruit_event_timer:.2f}",
        Align.TOP_RIGHT
    )
    def decision_str(decision: int):
        if decision == 0:
            return "FORWARD"
        elif decision == 1:
            return "LEFT"
        elif decision == 2:
            return "RIGHT"
        else:
            return "ERROR"
    title(
        "\n".join(
            f"Pl{i}Pwrs: {",".join(map(lambda pwr: str(pwr), pl.powerups)) or "None"}\nPl{i}D: {decision_str(pl.decision)}" for i, pl in enumerate(game_state.players)
        ),
        Align.BOTTOM_LEFT
    )

def pause(clock, msg="PAUSED"):
    title(msg, Align.CENTER, 72)
    pygame.display.update()
    while True:
        global will_pause
        clock.tick(DEBUG_FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
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
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
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
    



