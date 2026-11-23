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

## Two-panel option

Double-click **Start Micromaze Wall.cmd**, or choose **Micromaze** in
**Start LED Wall.cmd**. The wall uses your saved panel identifiers and layout.
Choose **Stack vertically** for a 64×32 view or **Side by side** for 128×16
while disconnected, then connect the wall. Close the single-panel game first.
Click the preview and press **Enter** to explore; the same movement keys work.
Space / P also pauses, Escape pauses, and R resets. The wall shows your elapsed
time and completion state. The EXIT message appears entirely on the topmost
panel (leftmost when side by side), clear of the seam. The optional PC map
remains in the single-panel app.

The maze renders one continuous camera view at the full canvas resolution.
Stacking adds vertical detail; side-by-side panels widen the view. Bezel gap
compensation works during play and keeps hidden rows/columns in the projection.
The wall streams at a 10-fps target while movement stays at 20 Hz. Pausing,
losing focus or a connection failure clears held movement keys.
See [LED Wall](../wall/README.md) for layout, rotation and connection details.
If movement tears at the seam, try **Align panel timing (experimental)** in the
wall controller. It delays the faster panel using recent completion replies;
toggle it during play to compare. Physical display synchronization is unverified.
Preview without Bluetooth with:

```powershell
.\.venv\Scripts\python.exe -m games.wall.app --maze
```

Movement simulates at 20 Hz. **Panel updates** selects Standard (10 fps) or
optional Windows (12 fps), with Standard fallback if unavailable. Both send
one acknowledged RGB PNG at a time and replace unsent old views. Reconnect
explicitly after a failure. The startup GIF is preserved; the panel holds the
last image when idle. Settings are in `.state/panel-settings.json` and summaries
in `captures/`. See [validation](../../docs/validation.md) for evidence.
