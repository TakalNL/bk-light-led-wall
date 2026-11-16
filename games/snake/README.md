# Snake: first playable prototype

A Windows desktop game for the verified 64×16 B.K. Light panel. The PC handles
keyboard input and game rules; the panel receives complete RGB PNG images using
the tested acknowledged transport. A local game preview works without Bluetooth.

## Play in this checkout

Double-click **Start Snake.cmd**. It uses the existing project environment and
remembers the selected panel privately in `captures/snake-settings.json`.
On first use, enter the panel identifier or exact advertised name and click
**Connect panel**. The current owner's checkout is configured locally.

- Click the game preview, then **Space** to start, pause or resume.
- **Arrow keys / WASD** steer. Direct reversal into the neck is rejected.
- **R / New game** resets the board; press Space to start again.
- Red is food, pale green is the head, green is the body. Walls and body are fatal.
- The board is 32×8 cells, each occupying 2×2 LEDs. Score stays on the PC.
- Start at **5 moves/sec**; the selector supports 3–8. Losing window focus pauses.
- **Play on PC only** disconnects the panel and enables local play.

The game starts ready, with no automatic movement. A lost connection or invalid
image reply pauses play; reconnect explicitly, then press Space to resume. It
does not reset or clear panel storage, save a game in a persistent slot, or
replace the saved startup GIF. Closing disconnects the worker. The last game
image may remain on the panel until another upload or power cycle.

## Setup elsewhere

Requires CPython 3.11+ with Tk, Windows Bluetooth, and this source checkout:

Run these commands from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[game]'
.\.venv\Scripts\python.exe -m games.snake.app
# Local play, without scanning or connecting:
.\.venv\Scripts\python.exe -m games.snake.app --preview
```

The base package pins the inspected `pypixelcolor` source commit and requires
Git to install it. The `game` extra supplies the game-specific dependencies.
Games and experiments use the same upstream builders, ACK manager and
send loop through our Windows connection adapter. The public `AsyncClient` has
passed basic connect/reconnect and PNG/GIF checks. A subsequent
[Starfall streaming comparison](../../STARFALL_STREAM_TESTS.md) favored keeping
the adapter for timing headroom; Snake's public-client path remains untested.
This is a source prototype; no standalone installer
or broad device-compatibility claim is included.

## Streaming and checks

One continuous connection, acknowledged RGB PNG uploads, non-saving slot 0 and
at most ten uploads per second by default. The optional
[Windows profile](../common/README.md#panel-update-profiles) targets twelve when
its connection preference is negotiated. Idle boards are not repeatedly uploaded. There
is one image in flight; newer game states replace unsent ones. A slow frame does
not end the game or create a backlog of old boards. Display timing can differ
from the PC preview; the timing shown in the window is the image reply time,
not measured keyboard-to-LED latency.

Connection, full transmitted bytes, image replies, frame timing and skipped
updates are recorded in ignored `captures/snake-*.jsonl`. App exceptions go to
`captures/snake-errors.log`. Logs include the target identifier and should be
reviewed before sharing. App-generated graphics use no downloaded artwork.

Tests cover growth, queued turns, collisions, legal tail movement, full-board
completion, RGB frame bounds, single-flight/latest-state streaming, bad replies
and idle disconnection. The UI also has a hidden-window control smoke check.
The earlier five-minute transport test passed 3000/3000 images; its final frame
was visually confirmed, but the owner was absent during the run. The owner then
confirmed the Snake prototype worked. Detailed input-to-display timing and
long-duration visual smoothness remain uninstrumented.
