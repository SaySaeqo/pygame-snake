# Snake Game

This is a Snake game project with networking capabilities. The game can be played in both host and client modes.

## Prerequisites

- Python 3.7 or higher
- `pip` (Python package installer)

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/SaySaeqo/pygame-snake.git
cd pygame-snake
```

### 2. Create a Virtual Environment

Create a virtual environment to manage dependencies:

```bash
python -m venv venv
```

Activate the virtual environment:

- On Windows:

  ```bash
  venv\Scripts\activate
  ```

- On macOS and Linux:

  ```bash
  source venv/bin/activate
  ```

### 3. Install Dependencies

Install the required Python packages using `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Running the Game

To run the game, execute the following command:

```bash
python snake.py

```

## Optional: Generate Executable with PyInstaller

If you want to generate an executable for the game, you can use PyInstaller.

```bash
pyinstaller --onefile snake.py

```

This will create a `dist` directory with the executable file `snake` (or `snake.exe` on Windows).

## Additional Information

- The game saves scores to `leaderboard.data`.
- The game can be played in both host and client modes.
- The game uses asyncio for asynchronous operations.