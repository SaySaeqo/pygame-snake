# Snake Game

Enhanced Snake with free movement and real time networking capabilities.

It has:
- Local mode for up to 4 players playing on 1 computer.
- Local network mode where 1 computer is playing role of the host and others are his client.
- Internet mode for connecting with Playfab external server (still under construction).
- Leaderboard saving results in `leaderboard.data` file.
- Local configuration saved in `config.data` file.
- Own menu system.
- Configurable keybindings.
- Configurable players' names.
- Infinite mode and 1 minute mode.
- Configurable window size.

While playing online, clients are adjusting to host's settings.

It uses self-made libraries:
- [pygameview](pygameview) for managing asynchronous pygame views (effectively making pygame asynchronous library using asyncio)
- [gamenetwork](gamenetwork) for managing TCP and/or UDP connections - making it easy for exchanging messages. Although, it will be eventually removed since TCP and UDP protocols does not work properly along itself creating situation in which both TCP and UDP packets are being dropped more frequently ([source](https://web.archive.org/web/20160103125117/https://www.isoc.org/inet97/proceedings/F3/F3_1.HTM)). It will be replaced with [enet](https://github.com/aresch/pyenet) library.

## Releases

For stable versions and some screenshots check [releases](https://github.com/SaySaeqo/pygame-snake/releases) subpage.

## Building from source

1. Install Python 3.7 or higher.
2. Create virtaul environment for python.
3. Install all dependencies from `requirements.txt`.
4. Run `snake.py`.


## License
This project is licensed under the GNU General Public License v3.0. See the LICENSE file for details.
