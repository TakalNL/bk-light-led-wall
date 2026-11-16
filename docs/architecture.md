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
