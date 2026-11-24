# Architecture

## Local service and browser

`src/led_matrix_hacker/service.py` owns saved setup, discovery, content, simulation
and session lifecycle. `server.py` exposes an aiohttp API and persistent browser
connection. Bundled HTML/CSS/JavaScript under `web/` needs no frontend build,
external assets or graphical desktop. The service does not import Tk.

The Bluetooth host runs the application; desktop and phone browsers talk to it
on the local network. Preview is software-rendered output, not LED readback.
A per-start token protects the API and authenticates the browser connection.
A six-digit code or QR gives a phone access without typing the long token.
There is one active controller with explicit takeover; other browsers observe.
Complete key sets, input release and a 1.5-second watchdog avoid stuck controls.
Browser loss/backgrounding pauses games without requiring a BLE disconnect.

Slow setup and media changes are serialized by an operation lock. A panel-card
change joins the existing BLE worker before starting the remaining/new set of
links. The configured mounting positions stay saved when a panel is excluded;
the active canvas is translated to its bounding box. Games reset and media is
cleared when changing the active set. Removing the last panel clears setup.

The service currently reconnects only on an explicit request. It does not
persist uploaded media or implement unattended desired-state recovery. Native
playback can change context after reconnect, so future recovery cannot assume
the panel still shows the last temporary PNG.

## Canvas and Bluetooth worker

`wall.py` defines validated tiles, mounting rotation, image/GIF fitting, canvas
splitting and immutable RGB frames. Gap pixels are omitted from uploads and
shown black in the preview. Overlaps and duplicate identifiers are rejected;
the worker also checks that two identifiers do not resolve to the same device.

`games/common/wall.py` owns one BLE loop/thread and a link per active panel.
Panels are discovered and verified before streaming. A latest-frame mailbox
replaces unsent frames instead of queuing a backlog. Each canvas is uploaded
concurrently, with at most one pending image per link; a barrier waits for every
completion reply before the next canvas. A failed/ambiguous transfer cancels
sibling uploads and closes the links rather than retrying partial images.

The wall targets at most 10 combined updates/s; a slow upload limits the actual
rate. Optional adaptive alignment delays faster panels using recent median
upload durations, bounded to 250 ms. This improved the observed test pattern;
it is not an atomic display swap or a shared hardware refresh clock.

Frames carry their own layout. The older Tk wall can therefore change gap
geometry after the in-flight canvas finishes. The web UI currently requires
disconnection for manual position/gap edits. Both require a new worker when
changing panel identities/order.

Animated media uses `native_animation.py` and Pillow to encode one native 64x16
GIF per tile after fitting the complete canvas, omitting gap pixels and undoing
mounting rotation. Immutable `NativePlayback` requests share the worker mailbox
with RGB frames. The worker drains any current upload, uploads all panel GIFs
with the temporary 0x65 preview destination, validates completion replies, then
sends their individual 15-byte restart headers concurrently. No ongoing frame
uploads or periodic restarts occur during native playback. Starts are approximate;
there is no shared device clock. A newer selection supersedes an upload before
restart. Any failed transfer cancels siblings and closes the session.

The shared timeline preserves GIF durations; requests faster than the observed
30-ms decoder floor are sampled on a 30-ms timeline while retaining loop length.
Pillow may merge identical panel frames but their encoded loop durations must
match. Encoding uses a global palette per panel and a 2-MiB per-panel limit.
Pausing publishes an RGB snapshot; playing again uploads/restarts the animation.
The software preview runs separately and resets its epoch after the restart ACKs.

## Backend responsibilities

The dependency is pinned to pypixelcolor commit
`c8cbaebca6df7797a7bcface8a1c4ca33e499973`; no application patch is required.

| Responsibility | Owner |
| --- | --- |
| Command builders, PNG/GIF framing, CRCs, ACK manager and send loop | pypixelcolor |
| Platform discovery, connection and GATT access | Bleak |
| Bounded connections, service checks, strict replies and tracing | `library_link.py`, `transport.py` |
| Identity parsing and verified-dimension guard | `protocol.py` |
| Optional scoped Windows connection hint | `windows_connection.py` |
| Lifecycle, layout, coordination, original rendering and controls | This application |

The application uses upstream builders/transport through an instrumented adapter,
not the public Client lifecycle. The public AsyncClient has separate hardware
checks. The [chunk-size contribution](../patches/README.md) is independent;
its submission does not imply a current upstream merge status.

Live frame uploads use acknowledged writes, RGB PNGs and non-saving slot 0, with
chunks up to 500 bytes bounded by the connection's supported limits. Full raw
RGB, indexed PNGs, fast writes and pipelining are not alternate production paths.

## Older desktop interfaces and Windows tuning

`games/common/app.py` and `launch.py` own the shared Tk shell, startup and input
lifecycle. Game `game.py` modules contain rules and Pillow renderers. The original
bitmap font lives in `graphics.py`. The web service reuses these renderers and
game models without importing the desktop shell.

`games/common/panel.py` provides the original single-panel game worker. Its
optional Windows profile requests throughput parameters and targets 12 uploads/s
only after acceptance and reported 15-ms/zero-latency parameters. Missing APIs,
refusal or unmatched negotiation fall back to Standard. The scoped WinRT request
is released on exit/failure and reacquired on reconnect. It accesses a private
Bleak backend object and may reduce concurrent Bluetooth capacity.

**That optional profile is not applied by the web/wall worker.** Earlier measured
single-panel 12-fps results do not describe the current wall. Timer-resolution
changes and fast-write variants remain experiments.

## Storage, packaging and evidence

| Entry point | Settings default |
| --- | --- |
| Windows standalone | `%LOCALAPPDATA%\LED Wall\wall-settings.json` |
| Source web service | `.state/web-wall-settings.json` |
| Older Tk wall | `.state/wall-settings.json` |
| Older single-panel games | `.state/panel-settings.json` |

The web service keeps timing/excluded-panel preferences in an adjacent
`.preferences.json` file. Captures contain session/frame/error summaries;
`--trace-packets` enables full transport details in tools that offer it.
Settings, captures and access credentials are private and ignored by Git.

`packaged.py` supplies standalone user-storage and browser defaults. The Windows
build script consumes a wheel-installed environment, bundles runtime/assets,
collects project/dependency notices and writes a ZIP plus checksum/build manifest.
Building Windows does not validate Linux or ARM; real BlueZ playback is pending.

Developer tools are under `tools/` and excluded from the application wheel.
Historical reports retain their conditions under `docs/archive/`. Private APKs,
research helpers, downloaded artwork and raw captures are not runtime dependencies.
