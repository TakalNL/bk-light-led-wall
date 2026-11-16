# Starfall

Double-click **Start Starfall.cmd**, connect the panel, click the preview and
press **Enter**. Or choose **Play on PC only**. See [installation](../../README.md).

- **Enter / P:** launch, pause or resume. **Escape:** pause.
- **Arrows / WASD:** move. **Space:** fire; **Auto-fire** fires continuously.
- **R / New game:** reset to three lives; Enter starts again.
- Losing focus or the panel connection pauses play.

Three waves of drones, weavers and gunners lead to a carrier boss. Enemy shots
and contact cost a life. Each hit shows a result briefly, then respawns the
ship with blinking protection. At zero lives the game shows OUT; defeating the
carrier shows WIN.

Cyan **T** capsules unlock twin cannons; yellow **R** capsules unlock rapid fire.
Fly into them to collect them. Upgrades survive a lost life and reset with a
new game. Points and lives remain visible on the PC; dots on the panel indicate
lives and collected upgrades.

The game simulates at 20 Hz. Choose **Panel updates** while disconnected:
Standard targets 10 uploads/s; optional Windows mode targets 12 and falls back
to Standard if its connection preference is unavailable. One acknowledged RGB
PNG is in flight; the latest state replaces unsent images. The PC preview is
not panel readback. Reconnect explicitly after a failure, then Enter resumes.
The panel holds its last image when idle; the saved startup GIF is preserved.

Settings live in `.state/panel-settings.json`, summaries in `captures/`.
See [validation](../../docs/validation.md) for measured results.
