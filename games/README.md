# Game prototypes

Each game keeps its code, launcher, documentation and tests in its own folder.
The shared desktop shell and acknowledged RGB streaming worker live in `common/`.
The main `src/led_matrix_hacker/` package contains the Bluetooth/protocol tools.

| Prototype | Launcher | Instructions |
| --- | --- | --- |
| Snake | [Start Snake.cmd](snake/Start%20Snake.cmd) | [Snake](snake/README.md) |
| Starfall | [Start Starfall.cmd](starfall/Start%20Starfall.cmd) | [Starfall](starfall/README.md) |
| Micromaze | [Start Micromaze.cmd](micromaze/Start%20Micromaze.cmd) | [Micromaze](micromaze/README.md) |

Each game directory contains `game.py` (rules/rendering), `app.py` (controller),
`tests/`, a README and a Windows launcher. The launchers find the project root
relative to their own location, so they use the existing root `.venv/` and
private `captures/` settings/logs. Only one game should connect to the panel at a time.

Before connecting, **Panel updates** lets you choose the default **Standard
(10 fps)** or optional **Windows (12 fps)** profile. Windows mode falls back to
Standard if its connection preference is unavailable or not negotiated. The
choice is remembered across all three games. See [profile details](common/README.md#panel-update-profiles).

For a local preview, run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m games.snake.app --preview
.\.venv\Scripts\python.exe -m games.starfall.app --preview
.\.venv\Scripts\python.exe -m games.micromaze.app --preview
```

Run all checks with `.\.venv\Scripts\python.exe -m pytest`; this includes the game
tests and the core Bluetooth/protocol tests. Run one game's checks by supplying
its directory, for example `-m pytest games/micromaze/tests`.
