# Shared game infrastructure

- `app.py`: desktop preview, connection controls, input/focus and update lifecycle.
- `launch.py`: shared command-line arguments, Tk startup and error reporting.
- `panel.py`: latest-state mailbox and single-flight Bluetooth worker.
- `profiles.py`: default 10-fps and optional Windows 12-fps output selection.
- `settings.py`: shared panel preferences.

Each game supplies its own rules, renderer, keyboard handler and status text.
The runtime uses pypixelcolor through `led_matrix_hacker/library_link.py`.

See [architecture](../../docs/architecture.md) for backend ownership and profile
behaviour, [development](../../docs/development.md) for settings/logs, and
[validation](../../docs/validation.md) for test evidence.
