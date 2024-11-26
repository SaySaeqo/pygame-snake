from snake_menu import *
import logging
from snake_utils import log
import asyncio

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    log().info("Starting the game")
    Config().load_from_file()
    create_window("Snake")
    asyncio.run(show_menu("SNAKE", main_menu))