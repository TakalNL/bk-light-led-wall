# Micromaze

An original Wolfenstein-style raycasting experiment for the verified 64x16
B.K.Light panel: walk through a small maze and find the glowing green exit.
There are no enemies, weapons, doors or time limit. Enter the green portal to win.
Blue, rust and grey wall regions, side shading and coarse brickwork help distinguish
corners at this resolution. All graphics and level data are made in this project.

Double-click **Start Micromaze.cmd**. It uses the saved panel target and connects
without starting movement. Close or disconnect Snake/Starfall first so only one
application uses the panel. Press **Enter**, then click the main window if it
doesn't have keyboard focus. The PC preview mirrors the panel image.

| Control | Action |
| --- | --- |
| W / Up, S / Down | Walk forward / backward |
| A / Left, D / Right | Turn left / right |
| Q / E | Strafe left / right |
| Enter / P | Start, pause or resume |
| Escape | Pause |
| R | Reset to the entrance, paused |
| M / Show map | Toggle an optional PC-only map; yellow is you, green is the exit |

The timer counts active game time. Losing application focus pauses play. Completing
the maze shows `EXIT` on the panel and the completion time on the PC. Enter after
winning starts a new walk. The same maze is used each time.

## Setup and local preview

Uses the same Python environment and optional dependencies as the other games:

Run these commands from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[dev,game]'
.\.venv\Scripts\python.exe -m games.micromaze.app --preview
.\.venv\Scripts\python.exe -m games.micromaze.app --connect
```

`game.py` contains deterministic movement, wall collision, DDA wall casting and
depth-occluded exit rendering. `app.py` reuses the desktop controls and shared
panel worker. Movement runs at 20 ticks/second; the latest view is sent as an RGB
PNG at at most 10 uploads/second by default. The optional
[Windows profile](../common/README.md#panel-update-profiles) targets 12. Both use one acknowledged image in flight. There is
no queue of old camera positions. Walls intentionally use a compressed vertical
projection for a readable view in just 16 rows. This is a tiny original maze,
not a port of Wolfenstein or its assets.

The established transport is unchanged: pinned `pypixelcolor` image builders,
our Windows adapter, 500-byte acknowledged chunks and PNG slot 0. It does not
replace the saved startup GIF. Detailed connection/frame logs remain private in
`captures/micromaze-*.jsonl`; callback errors go to `micromaze-errors.log`.
Connection errors pause the game; reconnect manually before resuming.

Automated checks cover map connectivity, a complete walk to the exit using normal
movement controls, collision/sliding, diagonal speed, DDA distances, portal
occlusion, and RGB packet sizes across sampled positions/headings. These cannot
establish readability or smoothness on the physical LEDs; those need the owner's
play test. Packet-size sampling does not cover every possible camera position.

Local validation: **164 tests passed**, including nine maze cases. A further
11,360 sampled views (five offsets per floor cell, 32 headings) had a largest
PNG application packet of **403 bytes**, within one 500-byte write. Hidden-window
checks exercised start, movement, pause, reset and the map toggle. The initial
ready view connected to the owner's verified panel and received the expected
`0500020003` image reply (309-byte packet, 56.0 ms reply). The owner subsequently confirmed that the prototype works on the panel; exact
input-to-display latency remains unmeasured.
