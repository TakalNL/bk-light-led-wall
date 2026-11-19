# Development

## Environment and tests

Use CPython 3.11+ with Tk, Git and the extras described in the [README](../README.md).
The current checkout uses `.venv`; its interpreter lives in `.tools/python`.
The editable pypixelcolor import comes from `.research/ipixel`. Preserve both
until replacing the environment with a normal installation of the pinned dependency.

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/experiments
```

If a restricted environment cannot use the system pytest temp directory, supply
a new workspace-local path with `--basetemp=.tools/test-tmp-unique`. The cache
provider is disabled because its filesystem writes hung in the original sandbox.
Tests use synthetic BLE objects and never access the real adapter.

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

The initial Git checkpoint preserves all pre-cleanup source and documents.
The archived [original brief](archive/project.md) retains its exact file contents;
other historical Markdown links are rebased to their new locations.
