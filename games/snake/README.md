# Snake

Double-click **Start Snake.cmd**, connect the panel, click the preview and press
**Space**. Or choose **Play on PC only**. Installation is in the [root README](../../README.md).

- **Space:** start, pause or resume.
- **Arrows / WASD:** steer; reversal into the neck is rejected.
- **R / New game:** reset; Space starts again.
- **Escape:** pause. Losing focus or the panel connection also pauses.
- **Moves / sec:** 3-8, default 5. This is separate from panel output rate.

The board has 32x8 cells, each occupying 2x2 LEDs. Red is food, pale green is
the head and green is the body. Walls and body collisions end the run. Score
stays on the PC.

Choose **Panel updates** while disconnected: Standard targets 10 uploads/s;
Windows targets 12 after negotiation and otherwise falls back to Standard.
Both send acknowledged RGB PNGs in non-saving slot 0, preserving the startup
GIF. Unsent states are replaced; there is one upload in flight. Reconnect
explicitly after a failure, then press Space to resume. The panel keeps its
last image when idle or disconnected.

Settings live in `.state/panel-settings.json`, summaries in `captures/`.
See [validation](../../docs/validation.md) for evidence and limitations.
