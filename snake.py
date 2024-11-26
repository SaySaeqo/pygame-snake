from snake_menu import *
import logging
from snake_utils import log
import asyncio

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    log().info("Starting the game")
    asyncio.run(show_menu("SNAKE", SnakeMenu().main_menu))