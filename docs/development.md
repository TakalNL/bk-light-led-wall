# Development

## Environment and tests

Use CPython 3.11+ and Git. Python 3.13.9 is the tested runtime. The headless
service needs no Tk or graphical desktop; the older desktop interfaces need Tk.
From a clean checkout on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,server,game]"
```

On Linux, use `python3 -m venv .venv` and `.venv/bin/python` for the equivalent
commands. BlueZ is needed for Bluetooth, but playback on Linux is unvalidated.
Installing dependencies and passing synthetic tests does not validate a Linux
Bluetooth adapter. The pinned upstream revision is fetched automatically; no
local research checkout or upstream patch is required.

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/experiments
```

If a restricted environment cannot use the system pytest temp directory, supply
a new workspace-local path with `--basetemp=.tools/test-tmp-unique`. The cache
provider is disabled because its filesystem writes hung in the original sandbox.
Tests use synthetic BLE objects and never access the real adapter.

The maintainer's original environment uses a local interpreter and an editable
reference checkout under ignored directories. Those are lab conveniences, not
application requirements. Keep existing local evidence/environments intact when
working in that lab; use a new environment to check a public installation.

The source layout is `src/led_matrix_hacker`, `games`, `tests` and `tools`.
Developer tools are deliberately excluded from the installed application package.

## Running games

```powershell
.\.venv\Scripts\python.exe -m games.starfall.app --preview
.\.venv\Scripts\python.exe -m games.starfall.app --connect
.\.venv\Scripts\python.exe -m games.starfall.app --settings .state/test-panel.json --capture-dir captures/test-session --trace-packets
```

All games share the launcher arguments. Default settings live in
`.state/panel-settings.json`. `--settings` isolates a test preference. Normal
logs contain connection, frame and error summaries; `--trace-packets` adds full
transport events. Identifiers/payloads in diagnostic captures remain private.

The separate [LED Wall controller](../games/wall/README.md) runs with
`python -m games.wall.app --connect`; its layout is saved in
`.state/wall-settings.json`. `--demo` starts the seam animation. Its CLI uses
`--settings` and `--capture-dir` but does not use single-panel game profiles.
`tools.diagnostics.wall_test --settings .state/wall-settings.json` exercises the
combined upload path with identify/demo frames and bounded cleanup.
`--maze` opens the wall's first-person maze. `--align-timing` in either the wall
controller or diagnostic enables optional adaptive start delays; the controller
also has a live checkbox. It aligns estimated upload completions, not verified
LED refresh timing. See the [wall instructions](../games/wall/README.md).

## Web service development

Install `.[server]` and run `python -m led_matrix_hacker.server`. Use
`--host 0.0.0.0` for LAN/phone access and `--open` to open the local access link.
The service is headless; static assets are packaged in `led_matrix_hacker/web`.
No frontend build step is required. Server tests use aiohttp's real HTTP and
WebSocket test clients plus synthetic workers and never touch Bluetooth.

`POST /api/pair` exchanges the six-digit code for the session token. Five wrong
attempts within one minute temporarily block code exchanges; already paired
clients continue working. Origin checks apply to pairing too. Codes and tokens
change on server restart. Authenticated `GET /api/access` returns LAN addresses
and the code; `/api/access/{index}/qr.png` generates a QR with the full access link.
Neither the code nor the QR is returned to unauthenticated viewers.

`GET /api/state` and `POST /api/{scan,layout,connect,disconnect,panel,mode,timing,media}`
require the printed token as a Bearer header. `/api/ws` accepts that token in
its first JSON message before publishing state or binary PNG previews. Claim
control with `{"type":"claim"}`; mutating HTTP calls also supply the returned
client ID in `X-LED-Controller`. `scan` is available to authenticated viewers.
WebSocket inputs are complete key sets, rather than unpaired down/up events.
The browser sends heartbeats while foregrounded; the watchdog releases stale
inputs even if its close/release message is lost.

Layout changes require disconnection. Timing alignment can toggle live. The
panel endpoint accepts `{"device":"<saved identifier>","action":"connect"}`
(or `disconnect` / `remove`) while connected. Disconnect preserves the mounting
positions and saves the panel in `excluded_panels` preferences; remove forgets
the panel, including the last entry. From idle, a panel-card connect starts that
panel alone; during playback it adds that panel to the active set. The global
connect resumes the selected set. The worker closes and joins before connecting
the replacement set, briefly interrupting remaining panels. Their canvas uses
the active bounding box, preserving relative positions/gaps; a sole remaining
panel renders at its own size. Games reset without starting; decoded media is
cleared and must be uploaded again. Browser control remains with the caller.
Disconnect stops updates rather than powering the panel off.

The operation lock serializes slow setup/media operations; each BLE worker still
allows only one image per panel in flight. API shape is a prototype contract,
not a promised stable home-automation API yet. Keep access links, identifiers,
packet captures and host logs private.

## Diagnostic toolkit

Read-only discovery uses the CLI:

```powershell
.\.venv\Scripts\python.exe -m led_matrix_hacker scan --timeout 15
.\.venv\Scripts\python.exe -m led_matrix_hacker inspect $deviceId --json
```

Supervised writes use modules from the project root; inspect `--help` before use:

```powershell
.\.venv\Scripts\python.exe -m tools.diagnostics.device_info --help
.\.venv\Scripts\python.exe -m tools.diagnostics.static_image --help
.\.venv\Scripts\python.exe -m tools.diagnostics.gif_animation --help
```

`tools/diagnostics` also contains the pixel/corner and public-client checks.
The old `examples/scan.py` and `inspect_device.py` wrappers were redundant with
the CLI and were removed. Other former `examples/<name>.py` runners retain
their names under `tools/diagnostics` or `tools/experiments`.

`tools/experiments` retains the streaming comparisons, grouped pixels, pipeline,
timer, native-pixel and animation fixtures. These are research tools, not app
features. The grouped command requires the specific upstream PR #88 checkout;
the normal pinned dependency does not provide it. Restore that private checkout
before reproducing the experiment, or clone its recorded commit.

## Build check

```powershell
.\.venv\Scripts\python.exe -m pip wheel . --no-deps --wheel-dir .tools/build-dist
```

Build isolation installs the declared setuptools backend if needed. This produces
a Python wheel, not a standalone Windows installer. Validate the
wheel from outside the source directory so editable imports cannot mask omissions.
The submitted upstream patch and reproduction notes are in [patches](../patches/README.md).

## Windows standalone preview

Build a wheel, then install it into a fresh environment with the tested Windows
constraints. The application and pypixelcolor must not be editable installs:

```powershell
.\.venv\Scripts\python.exe -m pip wheel . --no-deps --wheel-dir .tools/release-wheel
.\.venv\Scripts\python.exe -m venv .tools/bundle-venv
.\.tools\bundle-venv\Scripts\python.exe -m pip install -c tools/packaging/windows-constraints.txt '.tools/release-wheel/led_matrix_hacker-0.1.0-py3-none-any.whl[server,bundle]'
.\.tools\bundle-venv\Scripts\python.exe tools/packaging/build_windows.py --output dist/windows-preview
```

The script uses PyInstaller to bundle an onedir Windows x64 executable, the web
assets, timezone data, dependency notices and an exact build-environment manifest.
It creates a ZIP and SHA256 sidecar and refuses to replace an existing archive.
Use a new output directory for a later build. Builds stay in a fresh directory
under `.tools/windows-bundles`; no previous build is recursively removed.

Extract the whole ZIP and run `LED-Wall.exe`. The entry point opens the browser
and enables LAN access by default. Settings/captures use `%LOCALAPPDATA%\LED Wall`,
independently of the launch/extraction directory. `--no-open`, `--host`, `--port`,
`--settings` and `--capture-dir` override these defaults. No auto-connect occurs.

Test the extracted artifact from a separate directory without Python/Git on PATH.
Exercise discovery and real BLE output as well as browser/QR/game/media behavior;
successful compilation alone is not hardware validation. The current ZIP is a
local unsigned preview. The [MIT license](../LICENSE) is included alongside
dependency notices. Public release and the remaining acceptance checks are
pending. Building Windows does not validate Linux or ARM.

## Private archives

`archive/private/` is ignored by Git. ZIP files contain completed captures,
reference checkouts and selected old build/validation artifacts. Each has an
adjacent manifest with original workspace-relative paths, sizes and SHA-256
hashes. Contents are verified against the manifest before unpacked originals
are removed. ZIP member paths begin at the project root (for example `captures/`).

To recover a file, inspect the manifest, extract the required member to a
temporary directory, and check its SHA-256 before restoring it. Avoid overwriting
current settings or source. Reports refer to original capture filenames; those
filenames remain intact inside the archive. Keep the archives private: they
contain raw Bluetooth data and downloaded test artwork.

The maintainer privately preserves original project briefs, obsolete entry
points, maintenance notes and publication metadata. They are not application
dependencies. Public experiment reports remain under `docs/archive/`.
