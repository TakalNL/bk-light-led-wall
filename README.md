# LED Matrix Hacker

Three Windows desktop games for the B.K. Light panel sold by Action, article
**3226274**. Tested hardware is **64x16**, device type `0x83`, using iPixel Color.
The games run on the PC and send complete RGB images to the panel over Bluetooth.

| Game | Windows launcher | Controls and details |
| --- | --- | --- |
| Snake | [Start Snake.cmd](games/snake/Start%20Snake.cmd) | [Snake](games/snake/README.md) |
| Starfall | [Start Starfall.cmd](games/starfall/Start%20Starfall.cmd) | [Starfall](games/starfall/README.md) |
| Micromaze | [Start Micromaze.cmd](games/micromaze/Start%20Micromaze.cmd) | [Micromaze](games/micromaze/README.md) |

## Setup

Requires CPython 3.11+ with Tk, Git, and Windows Bluetooth. From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev,game]'
```

This checkout already has a working `.venv`. Double-click a launcher, enter the
panel identifier or exact unique Bluetooth name, and connect. Close the phone
app first; only one game can connect to the panel at a time. Choose **Play on
PC only** for local play without Bluetooth.

```powershell
.\.venv\Scripts\python.exe -m games.starfall.app --preview
```

The pinned [pypixelcolor](https://github.com/lucagoc/pypixelcolor) dependency
provides command framing, CRCs, chunks and acknowledgements. Our adapter adds
bounded connections, verified dimensions, strict reply checks and logging.

## Panel updates

Choose a profile while disconnected:

- **Standard (10 fps)** is the default.
- **Windows (12 fps)** requests a scoped throughput preference. It falls back
  to Standard if unavailable, refused or not negotiated within five seconds.

Both use acknowledged writes, one image in flight and the latest unsent game
state. Game speed is independent of panel output. PNGs use non-saving slot 0;
the saved startup GIF is preserved. A failed upload or connection pauses play;
reconnect explicitly before resuming. The panel holds its last image when idle.

Saved-address discovery returns when the panel advertises. Two checks reached
ready state in **1.56 and 2.91 seconds**, compared with about 16 seconds before.
These measurements depend on the tested host/panel. See [validation](docs/validation.md).

## Settings and logs

The games share `.state/panel-settings.json`; old `captures/snake-settings.json`
settings migrate automatically on first use. Session summaries are written to
`captures/`. Both locations are private and ignored by Git.

Use `--trace-packets` only when a full diagnostic capture is needed. Developers
can override `--settings` and `--capture-dir`; see [development](docs/development.md).

## Development

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m led_matrix_hacker scan --timeout 15
```

- [Architecture](docs/architecture.md): runtime code, backend ownership and profiles.
- [Compatibility](docs/compatibility.md): verified operations and limitations.
- [Development](docs/development.md): tests, diagnostics, packaging and private archives.
- [Validation](docs/validation.md): current evidence and historical reports.
- [Roadmap](docs/roadmap.md): remaining work before a distributable release.

`src/` contains the backend, `games/` the desktop games, `tools/diagnostics/`
supervised checks, and `tools/experiments/` retained research runners. Historical
reports and the original brief are indexed in [docs/archive](docs/archive/README.md).

This is a source prototype validated on one Windows host and panel. A standalone
installer, clean-machine validation and broader device testing remain outstanding.
