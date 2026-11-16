# LED Matrix Hacker

Investigating the B.K. Light flexible LED matrix sold by Action, article **3226274**.
The owner reports the label **3226274 | 37/2026** and the app **iPixel Color**.
The panel is verified as **64×16 (1,024 pixels)**, with `(0,0)` at the top-left,
x increasing right and y down. This supersedes the original brief's unverified
16×51 figure. Pixel writes and CRC-framed PNG image uploads work on the owner's unit.

First-contact result (2026-11-14): the panel was identified by an off/on comparison
and successfully inspected over BLE. It exposes service 00FA, FA02 writes and FA03
notifications, matching the candidate iPixel interface. A subsequent published
pixel-command experiment changed a corner pixel red → green → blue, visually
confirmed by the owner, without the phone app. The panel returned device type
`0x83`; the owner then confirmed all four 64×16 corner markers. The raw full-frame
reference did not render the image, but the PNG/CRC upload did: the owner confirmed
the border, corners, text and RGB bars. See [PROTOCOL.md](PROTOCOL.md).

The tools provide BLE scanning, GATT metadata inspection, explicit notification
capture and separate supervised write experiments. See [RESEARCH.md](RESEARCH.md) for the five requested source
reviews and the additional iPixel reference, [HARDWARE_TESTS.md](HARDWARE_TESTS.md)
for first contact, and [PROTOCOL.md](PROTOCOL.md) for evidence status.
[project.md](project.md) is the original project brief.

The current product goal is an installable application for other buyers of this
exact panel. [PRODUCT_PLAN.md](PRODUCT_PLAN.md) records the proposed release scope,
upstream reuse and compatibility checks still needed. [UPSTREAM_REPORT.md](UPSTREAM_REPORT.md)
is a local compatibility-report draft; nothing has been posted upstream.

All game prototypes live in [games/](../../games/README.md), with a folder for each
game's code, launcher, instructions and tests. Shared game infrastructure is in
`games/common/`.

Each game offers **Panel updates: Standard (10 fps)** and, on Windows, an
optional **Windows (12 fps)** profile. Choose before connecting; Windows mode
falls back to Standard if its connection preference is unavailable or not
negotiated. Existing settings retain the 10-fps default. See
[streaming profiles](../../games/common/README.md#panel-update-profiles).

The first playable desktop prototype is **Snake**: double-click
[Start Snake.cmd](../../games/snake/Start%20Snake.cmd), connect the panel, then press Space and use
the arrow keys or WASD. It includes a PC preview, pause/restart, score and frame
timing. See [Snake instructions](../../games/snake/README.md) for controls, setup and current limitations.

The second game is **Starfall**, a side-scrolling shooter with three enemy
types, enemy fire, twin-cannon and rapid-fire pickups, three lives and a final
carrier boss. Open [Start Starfall.cmd](../../games/starfall/Start%20Starfall.cmd); Enter launches,
arrows/WASD move, and Space fires. See [Starfall instructions](../../games/starfall/README.md). Close or
disconnect the other game before connecting to the same panel.

**Micromaze** is an enemy-free first-person raycasting experiment: explore a maze
and find the green exit. Open [Start Micromaze.cmd](../../games/micromaze/Start%20Micromaze.cmd), press
Enter, use W/S to walk and A/D to turn. M toggles a PC map. See
[Micromaze instructions](../../games/micromaze/README.md) for controls and limitations.

## Installation

Use standard CPython 3.11+, Git and a BLE-capable adapter. Git is needed to install
the pinned pypixelcolor dependency. From this directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\led-matrix.exe --help
```

If `python` opens the Microsoft Store or cannot run, install regular CPython
from [python.org](https://www.python.org/downloads/windows/), or use `py -3.13`
in the first command if that launcher is available. Avoid free-threaded builds
unless Bleak's Windows dependencies support the chosen interpreter.

For this checkout, a local Python 3.13.9 and `.venv` were prepared under ignored
directories, so the `.venv` commands above can be used immediately. No activation
or execution-policy change is needed. To recreate that environment with the
downloaded local uv binary:

```powershell
$env:UV_CACHE_DIR = "$PWD\.tools\uv-cache"
$env:UV_PYTHON_INSTALL_DIR = "$PWD\.tools\python"
$env:UV_PYTHON_BIN_DIR = "$PWD\.tools\bin"
.\.tools\uv\uv.exe python install 3.13
.\.tools\uv\uv.exe venv --python 3.13 --seed .venv
.\.tools\uv\uv.exe pip install --python .venv\Scripts\python.exe -e '.[dev]'
```

On Linux/macOS, use `python3 -m venv .venv`, `.venv/bin/python -m pip install -e '.[dev]'`
and `.venv/bin/led-matrix`. Grant Bluetooth access through the OS; macOS displays
device UUIDs instead of MAC addresses. Early macOS 12.0–12.2 requires service UUID
filters in Bleak and is not supported by this unfiltered CLI; update macOS first.

The base package installs Bleak and the pinned pypixelcolor backend, which also
provides Pillow. The `dev` extra includes pytest and constrains Pillow for image
tests. The optional `experiments` extra includes Pillow and
`tzdata` for cross-platform Berlin clock handling. Install it for the examples below:

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[dev,experiments]'
```

There is no general device driver or animation scheduler yet; experimental
write operations remain separate from the read-only discovery CLI.

## Backend and custom code

All game and experiment writes now use the same pinned
[pypixelcolor](https://github.com/lucagoc/pypixelcolor) builders, `AckManager` and
`send_plan`. The earlier custom PNG/GIF encoders, chunk loop and experimental
request manager have been removed. Device-size mappings and pixel/time commands
also come from upstream.

`library_link.py` retains our connection settings, logging, timeouts, strict reply
checks and verified-dimension guard. The unmodified public `AsyncClient` has now
passed connect/reconnect and owner-confirmed PNG/GIF playback on this unit; see
[PUBLIC_CLIENT_TESTS.md](PUBLIC_CLIENT_TESTS.md). A paired two-minute
[Starfall streaming trial](STARFALL_STREAM_TESTS.md) achieved 9.78 fps through
the default public client and 10 fps through the current adapter. Both looked
correct to the owner. A separate [local public-client patch](../../patches/README.md)
exposing `chunk_size=500` also completed all 1,200 updates at 10 fps, with correct
rendering confirmed. Games retain the adapter's lifecycle bounds and diagnostics
pending integration. Larger public-API uploads remain untested. Games, desktop UI, diagnostic content and hardware observations
remain project-specific. The failed raw-RGB reference is retained only for
reproducing that negative experiment. Historical captures describe the code used
at the time; new captures use the shared backend's `library_*` events.

## Discovery commands

Power one panel from a compatible 5 V USB source, enable the PC's Bluetooth,
and disconnect/close the phone app first. Scanning has **no name/service filter**
by default. It does not connect or request pairing.

```powershell
.\.venv\Scripts\led-matrix.exe scan --timeout 15
.\.venv\Scripts\led-matrix.exe scan --timeout 15 --output captures\scan-on.json
.\.venv\Scripts\led-matrix.exe scan --timeout 15 --name LED --json
```

Each result shows the platform identifier, name, available RSSI and advertised
services. An empty service list means none were advertised, not that GATT has
no services. RSSI comes from advertisement data, not the removed `BLEDevice.rssi` API.
Raw advertising payloads are excluded unless `--include-payloads` is supplied.
Do not infer panel dimensions from unknown manufacturer data.

Copy the current identifier of the panel identified by the off/on comparison:

```powershell
$deviceId = 'REPLACE_WITH_IDENTIFIER_FROM_SCAN'
.\.venv\Scripts\led-matrix.exe inspect $deviceId --output captures\gatt.json
.\.venv\Scripts\led-matrix.exe inspect $deviceId --json
```

Inspection connects once, enumerates all exposed services, characteristic UUIDs,
handles, properties, descriptor metadata, and writable/notifiable flags, then
disconnects. It does **not** read characteristic/descriptor values, subscribe,
send handshakes, or write application commands. The OS may exchange normal
connection, discovery and security traffic; this is read-only at the application
protocol level. A unique exact advertised name is also accepted; duplicate names
are rejected. Device identifiers are preferred.

Notification capture is opt-in and requires the exact characteristic UUID or
handle found by inspection:

```powershell
$notifyUuid = 'REPLACE_WITH_FULL_UUID_FROM_GATT_INSPECTION'
.\.venv\Scripts\led-matrix.exe listen $deviceId --characteristic $notifyUuid --duration 30 --max-events 100 --output captures\notifications.jsonl
```

The OS normally enables notifications through a CCCD descriptor write. `listen`
sends no display commands and cannot observe another app's Bluetooth writes.
It streams UTC timestamps, monotonic elapsed time, UUID/handle, byte count and
hex payload to stdout and optionally a JSONL file. It stops at the duration or
event limit. Zero notifications is a valid result, particularly without commands.
Notifications may require initialization that we deliberately do not attempt yet.
Connection loss returns an error and keeps already flushed events.

All output paths must have existing parents; existing files are never overwritten.
Scan/inspect JSON is saved only with `--output`; `--json` prints it to stdout.
Partial/empty output can remain after an error, so use a new filename on retry.
Use `Ctrl+C` to stop. Exit codes: 0 success (including empty scan), 1 operational
error, 2 invalid CLI arguments, 130 interruption. Use `--scan-timeout` and
`--connect-timeout` with `inspect`/`listen` for slower discovery/connections.

Alternate invocation, examples and hardware-free tests:

```powershell
.\.venv\Scripts\python.exe -m led_matrix_hacker --help
.\.venv\Scripts\python.exe examples\scan.py --timeout 15 --json
.\.venv\Scripts\python.exe examples\inspect_device.py $deviceId --json
.\.venv\Scripts\python.exe -m pytest
```

## Reproduce the first pixel

This experiment **writes to the display**, unlike the discovery CLI. After
identifying the target and inspecting its GATT interface:

```powershell
.\.venv\Scripts\python.exe examples\pixel_test.py $deviceId --hold 8 --output captures\pixel-test-new.jsonl
```

It verifies 00FA/FA02/FA03, enables FA03 notifications and sends exactly three
published pixel commands at `(0,0)`: red, green and blue. Each color lasts eight
seconds with `--hold 8` (default four; also supports twelve). Watch the panel once
the log reports `ready`; discovery/connection happens first. The final color is
blue. No initialization/time query or persistent image upload is sent.

The owner's unit rendered the expected colors. The later corner test verified
the 64×16 coordinate endpoints; power-cycle persistence remains untested. A later
PNG sprite-streaming experiment is documented below.
A completed GATT write alone
does not confirm rendering; record your visual result separately. The regular
`led-matrix scan` / `inspect` commands retain their read-only behavior.

The Windows execution sandbox permitted scans but failed to open the device;
running metadata inspection and this experiment in the normal host context worked.
The successful host command still used BLE, with USB supplying power.

## Grid and static-image experiments

These examples send documented application commands and record replies; they are
not read-only inspections. Use fresh output filenames and the identified device:

```powershell
# Information request also synchronizes panel time-of-day to Berlin local time.
.\.venv\Scripts\python.exe examples\device_info.py $deviceId --timezone Europe/Berlin --output captures\info-new.jsonl
# Three-pixel L markers at the proposed four corners; no background clearing.
.\.venv\Scripts\python.exe examples\corner_test.py $deviceId --width 64 --height 16 --output captures\corners-new.jsonl
# One generated diagnostic PNG with CRC and slot 0 (reference non-saving mode).
.\.venv\Scripts\python.exe examples\static_image.py $deviceId --format png --windows-cached-services --output captures\image-new.jsonl --preview captures\image-new.png
```

The information reply uses a source-derived type-to-size map; unknown codes yield
no dimensions. The owner's `0x83` mapped to 64×16, then colored corner markers
provided independent visual confirmation. Version components are `[14,2]` and
`[7,4]`; the controller chipset and detailed version semantics remain unknown.

The static example generates a border, colored corners, `64x16` label and RGB bars.
PNG mode uses the observed information/version exchange, standard CRC32 and slot
0. The owner visually confirmed this image; FA03 returned `05 00 02 00 03`.
The optional `--format raw` reproduces the **failed** raw-frame reference test:
all 13 chunks completed, but the owner saw startup artwork rather than our image.
That response is not proof of successful rendering. Do not use raw mode as a
supported image path. Both modes reject unverified grid sizes in their encoders.

Captures retain all bytes; stdout abbreviates large payloads. Frames are split
into at most `min(244, MTU-3)` bytes per acknowledged GATT write and paced after
completion. There is no background queue or retry of a partial frame. If connection
fails before application writes, a new attempt uses new filenames. For repeated
GATT-unreachable errors, disconnect other clients and check connection state.
On this Windows host, fresh GATT enumeration repeatedly failed even after a panel
power cycle. A target-only diagnostic connected using the already verified FA
layout from Windows' cache. `--windows-cached-services` opts into that workaround
and limits enumeration to the FA service; use it only after a fresh inspection has
verified the target's layout. It is Windows-only; omit it on Linux/macOS. The
discovery CLI's normal enumeration defaults are unchanged. The evidence supports
this workaround, not a universal diagnosis of all connection failures.
Visual questions should follow the `finished` event, not precede it.

## Boundaries and next step

No scans or connections are run by the test suite. Nearby device identifiers and
capture files are sensitive: review before sharing. `captures/` data, downloaded
reference sources in `.research/`, local tools and virtual environments are ignored.
Only save unrelated nearby-device data when needed to distinguish the panel.

If nothing appears, compare panel off/on scans, increase duration, verify the
adapter and app disconnection, and check OS Bluetooth permissions. BLE absence
does not establish Bluetooth Classic; inspect the official app's capture/OS
Bluetooth discovery separately. Do not try arbitrary writes or forced pairing.

First contact, pixel control, grid/orientation and one static PNG upload are now
verified. At the reported two-metre desk placement on a separate USB supply,
the initial three attempts failed before application writes. After the owner
installed the PC antennas, three fresh connections all uploaded PNGs and received
the expected reply; the owner confirmed the final ANT3 image. Advertisement RSSI
improved from -101 dBm to -67 through -74 dBm. This verifies operation there in
three short trials; longer streaming results are below and maximum range remains unmeasured.
See [RANGE_TESTS.md](RANGE_TESTS.md) for timings and evidence.

A subsequent ten-second sprite pass at **2 fps** completed 20/20 PNG uploads with
the expected reply, and the owner confirmed regular movement and END with no
glitches. A follow-up at **5 fps** added a visible `01/50`–`50/50` counter:
50/50 frames were acknowledged over ten seconds, and the owner confirmed normal
counter progression with no glitches. A **one-minute 5 fps check** then completed
300/300 uploads without retries or connection failures; the owner saw all frames
but reported possible uneven pacing. Reply intervals varied from 110 to 295 ms;
exact screen timing was not measured. These verify bounded host streaming at the
same placement; uniform display timing, host-streaming rates above 5 fps and runs beyond one minute
remain untested. See
[ANIMATION_TESTS.md](ANIMATION_TESTS.md) for timings and the repeat command.

**Panel-local GIF playback also works:** a single 4 KB numbered GIF upload
returned `0500030003`; the PC disconnected, and the owner confirmed the animation
kept looping with steady-looking timing. The GIF encodes twenty 200 ms frames
and uses slot 0. No per-frame Bluetooth streaming is needed for that loop.
See [GIF_TESTS.md](GIF_TESTS.md) for the format, evidence and reusable example.
An online-art follow-up verified a native-size 44-frame eyes GIF using two
upload windows. In a labelled **10/20/25/50 fps** comparison, the owner confirmed
all four settings worked and looked progressively faster. A **528-frame GIF at
encoded 20 fps** then uploaded across twenty windows; the owner confirmed the
counter reached 528 and looped correctly after disconnect. Its 239 KiB upload
took about 55 seconds. Exact physical frame rate and hardware capacity ceilings
remain unmeasured; 528 frames at 50 fps were not tested.
See [EYES_BENCHMARK.md](EYES_BENCHMARK.md) and [ART_SOURCES.md](ART_SOURCES.md).
Exact display timing and the panel's capacity limit remain unmeasured; later
power-cycle and larger-file results are below.
See the checklist and protocol ledger for recorded evidence and remaining unknowns.

## Active library-based panel tests

[LIBRARY_PANEL_TESTS.md](LIBRARY_PANEL_TESTS.md) records the current capacity,
retention and live-update experiments using the pinned `pypixelcolor` builders,
ACK manager and send loop with our instrumented Windows connection adapter.
The library's fast GIF transport returned completion replies but visibly froze
twice; acknowledged uploads recovered playback. A small twenty-frame GIF also
worked with 500-byte acknowledged chunks. Full PNG updates did not sustain the
10/20 fps schedules with the original antialiased test HUD. A later compact
RGB bitmap HUD fits a complete image into one acknowledged write and achieved
100/100 frames at scheduled **10 fps**, visually confirmed. At 15/20 fps the
script stopped when it fell behind schedule; this does not establish a physical
panel frame-rate ceiling. A four-bit indexed PNG received a completion reply
but displayed black, so it is not a supported optimization.

A later [public-client fast-mode comparison](FAST_MODE_TESTS.md) completed a
fully watched two-minute stream of small RGB PNGs at **10 fps** with correct
rendering. At a requested 15 fps, fast and acknowledged modes both averaged about
11 fps, and the owner noticed brief pauses/missing frames in both. Fast mode
showed no convincing speed advantage for this workload; games retain their
acknowledged 10-fps default. The earlier fast GIF failures remain unresolved.

[GROUPED_PIXELS_TESTS.md](GROUPED_PIXELS_TESTS.md) records a separate sparse
Snake experiment using the proposed upstream grouped-pixel builder, with a
full-PNG control. This remains an isolated experiment; games keep the existing
transport.

[PNG_PIPELINE_TESTS.md](PNG_PIPELINE_TESTS.md) records the isolated comparison
of one versus two outstanding PNG uploads, with serialized acknowledged writes
and separate completion-reply accounting. The sequential control reached 11.08
completion replies per second at a requested 15 fps. A bounded overlapping pair
received only one final completion reply and timed out; pipelining remains an
unverified transport and is not used by the app.

[WINDOWS_CONNECTION_TESTS.md](WINDOWS_CONNECTION_TESTS.md) records a scoped
Windows throughput preference using the verified sequential PNG transport.
An initial 30-second pair improved completion-reply throughput from 10.85 to
12.96 uploads per second at a requested 15 fps. The owner confirmed correct
rendering but could not judge smoothness. A two-minute run at requested 12 fps
completed 1,429/1,440 uploads, averaging 11.91 per second, with all expected
completion replies. The owner watched the full two-minute run and confirmed
correct rendering throughout. The preference was released and the connection
closed; the app's defaults remain unchanged.

[Follow-up fast-write and pacing tests](WINDOWS_TRANSPORT_PACING_TESTS.md)
found no additional speed from fast writes with the throughput preference.
A scoped 1-ms timer request improved typical host scheduling precision, while
both two-minute runs remained near their 12-fps cap. The timer run had one
scheduled state skipped versus none in its control; it does not establish a
higher FPS ceiling or uniformly better timing.
The owner watched the fast and 1-ms timing runs and confirmed correct rendering
throughout both. All temporary requests were released and the sessions closed.

Within one continuous connection, acknowledged pixel commands added green beside
red and erased red while preserving green, visibly one pixel at a time. A static
probe also showed pixel drawing switched away from an uploaded PNG. Fast native
pixel animation visibly corrupted; it is not a verified game-rendering path.
These results qualify transport timings with independent visual observations.

Larger slot-0 GIF tests now have owner-confirmed playback through **1,024,
2,048 and 4,096 frames**. The largest file is 1,915,364 bytes, with a
204.8-second encoded loop at 20 fps; upload took 216.8 seconds using 500-byte
acknowledged chunks. This is a working lower bound, not a measured maximum.
The first 2,048-frame attempt was interrupted for an owner-requested unplug;
its fresh retry succeeded. A separate slot-1 save of our tiny original twenty-frame
GIF survived an owner-performed power cycle and resumed automatically after the
boot animation. Large-file persistent capacity remains unmeasured.

A five-minute compact RGB follow-up completed **3,000/3,000** expected replies
at scheduled 10 fps in 300.016 seconds without reconnects or timing stops. The
owner confirmed final counter 3000 but was absent during playback; continuous
visual smoothness and every intermediate rendered frame remain unverified.
