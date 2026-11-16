# Micromaze

Explore an original first-person maze and find the green exit. There are no
enemies or time limit. Double-click **Start Micromaze.cmd**, connect, click the
preview and press **Enter**. See [installation](../../README.md).

| Control | Action |
| --- | --- |
| W / Up, S / Down | Walk forward / backward |
| A / Left, D / Right | Turn left / right |
| Q / E | Strafe left / right |
| Enter / P | Start, pause or resume |
| Escape | Pause |
| R | Reset to the entrance, paused |
| M / Show map | Toggle the PC map; yellow is you and green is the exit |

The timer counts active play. Finding the exit shows your completion time;
Enter starts another walk. Losing focus or the connection pauses play.

Movement simulates at 20 Hz. **Panel updates** selects Standard (10 fps) or
optional Windows (12 fps), with Standard fallback if unavailable. Both send
one acknowledged RGB PNG at a time and replace unsent old views. Reconnect
explicitly after a failure. The startup GIF is preserved; the panel holds the
last image when idle. Settings are in `.state/panel-settings.json` and summaries
in `captures/`. See [validation](../../docs/validation.md) for evidence.
