# Architecture

## Application

`games/common/app.py` owns the desktop preview, input lifecycle, pause/focus
handling and connection UI. `launch.py` shares argument parsing, Tk setup and
error handling. Each game's `app.py` supplies controls and status text, while
`game.py` owns its simulation, rules and 64x16 RGB renderer.

`games/common/panel.py` runs one Bluetooth worker. A latest-state mailbox
replaces unsent boards; it never queues a backlog. There is one image in flight.
Unknown replies or disconnects stop the worker and pause the game. Partial
transfers are not automatically retried.

The original bitmap font lives in `led_matrix_hacker/graphics.py`, independent
of the retained animation experiments.

## Combined display

`led_matrix_hacker/wall.py` defines validated panel positions, clockwise mounting
rotation, canvas splitting, immutable RGB frames and image/GIF fitting.
`games/common/wall.py` owns multiple BLE links on one worker loop, verifies all
panels before uploads and sends each canvas version concurrently. A completion
barrier waits for every panel before selecting the latest unsent canvas. Any
failure cancels sibling uploads and closes all links without retrying partial
frames. Layout gaps are permitted; overlap and duplicate physical devices are
rejected. The wall uses Standard pacing, targeting at most 10 combined frames/s.

`games/wall/app.py` provides the Tk controller, preview, layout editor, discovery,
identify/demo modes, media playback and Snake on the full canvas. Snake's grid
dimensions default to the original 32×8 cells for existing launchers. The wall
uses `.state/wall-settings.json`, separately from single-panel game settings.
There is no verified hardware refresh synchronization across panels.

The wall's bezel gap control adjusts uniform row/column spacing from 0 to 32
pixels, including while connected. Each immutable canvas frame carries its own
layout, so image pixels and compensation change together after the current
multi-panel upload completes. Device identities/order remain fixed until
disconnect. Hidden virtual rows/columns are omitted from uploads and blacked
out in the preview. Positions persist the gap without changing the settings
schema; custom layouts continue to use individual coordinates.

## Backend ownership

The dependency is pinned to pypixelcolor commit
`c8cbaebca6df7797a7bcface8a1c4ca33e499973`.

| Responsibility | Owner |
| --- | --- |
| Command construction, PNG/GIF framing, CRCs, ACK manager and send loop | pypixelcolor |
| BLE platform discovery, connection and GATT access | Bleak |
| Connection bounds, service checks, strict image reply checks and tracing | `library_link.py` and `transport.py` |
| Device information validation and verified-dimension guard | `protocol.py` |
| Windows connection preference and its cleanup | `windows_connection.py` |
| Game rules, rendering, controls, scheduling and preferences | This application |

The app uses upstream builders and transport through an instrumented adapter,
not the public Client connection lifecycle. The public AsyncClient has separate
successful connection/upload tests. The public chunk-size proposal is
[PR #90](https://github.com/lucagoc/pypixelcolor/pull/90); its patch is in [patches](../patches/README.md).

## Output profiles

Standard keeps the established minimum 100-ms interval between upload starts.
The optional Windows profile requests throughput-optimized parameters and
targets 12 uploads/second only after acceptance and a reported 15-ms interval
with zero peripheral latency. Refusal, missing APIs or unmatched negotiation
fall back to Standard; the UI shows that result and the requested choice is
retained for the next connection.

Windows mode uses fixed deadlines to avoid accumulating sleep overshoot. It
skips elapsed slots and sends the current board. Both profiles use acknowledged
writes, chunks up to 500 bytes capped by MTU, complete RGB PNGs and slot 0.
Fast writes and timer-resolution changes are experimental only.

The WinRT request uses a private Bleak backend object. It is held for the
connection and released on normal exit, errors and cancellation. Reconnect
acquires a fresh request. Initial parameters do not guarantee the interval
throughout the session; the preference can also reduce concurrent BLE capacity.

## State and diagnostics

`.state/panel-settings.json` holds the shared panel target and requested profile.
`recording.py` writes game connection/frame/error summaries by default. The
`--trace-packets` option enables full transport events for diagnosis.

Developer runners and their fixtures live under `tools/`; the installed games
do not import them. Experimental regression tests live in `tests/experiments/`.
