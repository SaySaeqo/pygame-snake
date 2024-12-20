import menus
import logging
import asyncio
import pygameview
import dto
import pygameutils
import constants

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # logging.basicConfig(level=logging.INFO, filename="snake.log")
    # logging.basicConfig(level=logging.INFO, filename="performace.log", filemode="w")
    dto.Config().load_from_file()
    pygameutils.create_window(constants.WINDOW_TITLE)
    asyncio.run(pygameview.common.show_menu("SNAKE", menus.main_menu))