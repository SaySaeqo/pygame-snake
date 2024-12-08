import menus
import logging
import asyncio
import pygameview
import dto
import constants
import pygameutils

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # logging.basicConfig(level=logging.INFO, filename="snake.log")
    constants.LOG.info("Starting the game")
    dto.Config().load_from_file()
    pygameutils.create_window("Snake")
    asyncio.run(pygameview.common.show_menu("SNAKE", menus.main_menu))