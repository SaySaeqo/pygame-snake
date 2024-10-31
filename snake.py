from windowfunctions import *
from decisionfunctions import control_snake
import asyncio
import logging
import host
import client
from snake_utils import *

async def main():
    snake_menu = SnakeMenu()

    while True:
        snake_menu.run()

        options = Options(
            diameter=30,
            speed=4,
            time_limit=60,
            rotation_power=4
        )

        if snake_menu.network.is_active:
            if snake_menu.network.is_host:
                await host.run_host(snake_menu.names[:snake_menu.number_of_players], options, snake_menu.control_functions)

                continue
            else:
                # TODO brak systemu obsługi wyjścia z gry po udanym połączeniu
                await client.run_client(snake_menu.network.host_address, snake_menu.names[:snake_menu.number_of_players], snake_menu.control_functions)

                continue

        game_state = GameState()
        game_state.init(options.diameter, snake_menu.number_of_players, options.speed)

        async with asyncio.TaskGroup() as tg:
            for snake, func in zip(game_state.players, snake_menu.control_functions):
                tg.create_task(control_snake(func, snake, options.fps))
            scores = await run_game(game_state, options)

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