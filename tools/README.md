# Developer tools

Run modules from the project root with `.venv/Scripts/python.exe -m ...`.
Use `--help` before a hardware write and keep its capture private.

| Location | Purpose |
| --- | --- |
| `diagnostics/device_info.py` | Verified panel information and versions |
| `diagnostics/static_image.py` | RGB PNG diagnostic; historical raw mode is unsupported |
| `diagnostics/gif_animation.py` | Original numbered GIF upload check |
| `diagnostics/corner_test.py`, `pixel_test.py` | Bounded coordinate checks |
| `diagnostics/public_client_test.py` | Public AsyncClient lifecycle/upload check |
| `diagnostics/wall_test.py` | Shared-canvas identify/demo and optional timing alignment |
| `packaging/build_windows.py` | Standalone Windows ZIP from a clean wheel-installed environment |
| `maintenance/archive_private.py` | Verified private archives with hashes; never deletes source files |
| `experiments/public_game_stream.py` | Matched public-client/adapter replay |
| `experiments/windows_connection_stream.py` | Connection preference, fast-write and timer comparisons |
| `experiments/grouped_snake_stream.py` | Optional upstream PR #88 tests and concatenation probe |
| `experiments/png_pipeline_stream.py` | Unsupported two-image pipeline investigation |
| `experiments/library_panel_tests.py`, `pixel_session.py` | Older supervised transport probes |
| `experiments/sprite_animation.py`, `animation.py`, `local_animation.py`, `art_animation.py`, `raw_rgb.py` | Retained animation/image fixtures and historical RGB format |

All active app code is under `src/` and `games/`. These tools are excluded from
the application wheel. Their tests remain under `tests/experiments/`. The normal
suite skips four grouped-pixel cases unless the optional upstream command is
available; the exact checkout commit is recorded in the archived report.

Use `python -m led_matrix_hacker scan` and `inspect` for general discovery;
the two old example wrappers were removed. See [development](../docs/development.md)
for commands and [the research archive](../docs/archive/README.md) for evidence.
