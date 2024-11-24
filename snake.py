from decisionfunctions import control_snake
import asyncio
import logging
from snake_utils import *
from snake_menu import *

async def main():
    snake_menu = SnakeMenu()

    while True:
        await snake_menu.run()

        options = Options()

        game_state = GameState()
        game_state.init(options.diameter, snake_menu.number_of_players, options.speed)


        for snake, func in zip(game_state.players, snake_menu.control_functions):
            asyncio.create_task(control_snake(func, snake, options.fps))

        await apygame.run_async(ReadyGoView(game_state, GameView(game_state, options)), fps=options.fps)

        scores = game_state.scores

        # save scores
        with open("leaderboard.data", "a") as file:
            for idx, score in enumerate(scores):
                file.write(f"{snake_menu.names[idx]}: {score}\n")
            names_combined = " + ".join(sorted(snake_menu.names[:snake_menu.number_of_players]))
            file.write(f"{names_combined}: {sum(scores)}\n")

        show_scores(scores, snake_menu.names)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    log().info("Starting the game")
    asyncio.run(main())