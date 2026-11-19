# LED Wall

Connect multiple verified 64×16 panels as one logical RGB display. Launch
**Start LED Wall.cmd**, or run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m games.wall.app --connect
```

The confirmed two-panel setup is stacked: panel 1 at `(0,0)` and panel 2 at
`(0,16)`, giving **64×32** pixels. Its identifiers and layout are saved locally
in `.state/wall-settings.json`. Close other games and the phone app before
connecting. The original single-panel game launchers retain their own settings.

## Layout

While disconnected, select a panel row and edit its Bluetooth identifier,
X/Y position and rotation, then **Apply panel**. Coordinates describe the panel's
top-left corner on the shared canvas; X goes right and Y goes down. Rotation
describes clockwise physical mounting and is corrected in software. At 90/270
degrees a panel occupies 16×64 pixels.

**Stack vertically**, **Side by side** and **Reverse order** make common changes
quick. Add/remove panels for larger arrangements. Offsets and gaps are allowed;
overlaps, duplicate devices and canvases larger than 512×512 are rejected.
Sixteen panels is a software limit, not a verified Bluetooth capacity.

**Bezel gap (pixels)** applies variable compensation to a vertical stack or
horizontal row. Choose 0–32 whole pixels with the arrows, or type a value and
press **Apply gap** / Enter. This control works during playback without
reconnecting. A value of 0 turns compensation off. For two stacked panels,
3 pixels places the lower panel at Y=19 and creates a 64×35 virtual canvas:
rows 16–18 are hidden behind the physical gap. The preview shows those rows
as black. The value is saved in the panel positions and restored next time.
Layout presets use the chosen gap; custom arrangements still use X/Y positions.
Snake currently requires zero compensation and no other layout gaps.

**Scan Bluetooth** finds advertised LED names and populates the identifier
dropdown. Apply a different identifier to each panel. The identify preview
shows numbered, coloured outlines; a white square marks each panel's top-right
corner. The dashed outlines and small labels in the preview are overlays and
are not uploaded with normal content.

## Content

- **Identify** sends numbered panel markers.
- **Seam demo** animates a ring and line across the whole canvas.
- **Snake** uses the full canvas with 2×2-pixel cells. Space starts/pauses;
  arrows/WASD steer; R restarts. Click the preview for keyboard focus. Snake
  requires a rectangle with no gaps. Other game launchers still use 64×16.
- **Open image / GIF** fits content to the whole canvas before splitting it.
  Fit preserves the whole image with black padding; Fill crops to cover the
  canvas; Stretch resizes to its dimensions. Transparency is composited on black.
  GIF disposal and frame durations are decoded by Pillow; animations loop.
- **Pause / Play** freezes/resumes animation. **Clear** sends black.

Content can be previewed locally while disconnected. GIFs stream from the PC
as RGB PNG frames, so the controller must remain running. Short GIF frames may
be skipped at the wall's 10-fps target. Up to 1,000 decoded frames and 16 million
output pixels are retained in memory.

## Connection behavior

All panels must connect and pass the existing 64×16 device check before any
content is uploaded. Each canvas version is cropped/rotated into per-panel RGB
PNGs and uploaded concurrently. The next canvas waits for every completion
reply. Newer content replaces unsent frames instead of creating a backlog.
Each panel has at most one upload pending. The wall uses Standard pacing with
no Windows throughput hints.

This coordinates software frames; the panels have no verified shared refresh
clock or atomic multi-panel swap. A small visible timing difference at the seam
is possible. A failed link/upload stops the whole session, closes the other
connections and requires explicit reconnect. Partial uploads are never retried
automatically. Slot 0 preserves saved startup content. Panels hold their last
image when idle/disconnected.

Session summaries go to `captures/wall-ui-*.jsonl`; UI errors go to
`captures/wall-errors.log`. Override paths with `--settings` and `--capture-dir`.

## Hardware diagnostic

```powershell
.\.venv\Scripts\python.exe -m tools.diagnostics.wall_test --settings .state/wall-settings.json --seconds 10
```

This sends identify labels for two seconds, runs the seam animation, restores
the labels and disconnects. It creates a PNG preview and JSONL capture. Use it
with the controller disconnected. Completion replies verify accepted uploads;
visual alignment still needs an observer.
