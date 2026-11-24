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
- **Snake** uses the full canvas with 2×2-pixel cells. Choose Snake, then press
  Enter / Space or click **Pause / Play** to start or pause; arrows/WASD steer,
  R resets, and Escape pauses. Click the preview for keyboard focus. Snake
  requires a rectangle with no gaps. Other game launchers still use 64×16.
  On two panels, losing shows **GAME** on the top/left panel and **OVER** on
  the bottom/right panel, with each word centred on its own screen.
- **Micromaze** renders the first-person maze across the full canvas, including
  bezel compensation and rotated panels. W/S or Up/Down walks, A/D or Left/Right
  turns, and Q/E strafes. Enter / Space / P starts or pauses; Escape pauses and
  R resets. Find the green exit; elapsed time and completion appear below the
  preview. Movement runs at 20 Hz independently of the 10-fps wall output.
  Losing focus or a connection pauses play and clears movement keys. Use
  **Start Micromaze Wall.cmd** or `--maze` to open this mode directly.
- **Open image / GIF** fits content to the whole canvas before splitting it.
  Fit preserves the whole image with black padding; Fill crops to cover the
  canvas; Stretch resizes to its dimensions. Transparency is composited on black.
  Pillow handles resizing, GIF disposal, transparency and encoding. Large sources
  are filtered when reduced; small pixel art stays crisp when enlarged.
  Animated GIFs are automatically cropped around bezel gaps and rotated into one
  native 64x16 GIF per panel, uploaded once, then restarted concurrently. Playback
  runs on the panels, without the streamer's 10-fps ceiling. Starts are approximate,
  not a shared hardware clock; a small lead or drift can remain. Source timing is
  preserved; frames faster than 30 ms are sampled without slowing the full loop.
  Pause sends the current preview frame; Play uploads and restarts the loop.
  A gap or fit change automatically rebuilds the panel GIFs. Each generated panel
  GIF is limited to 2 MiB. An oversized animation reports an error before uploading.
- **Pause / Play** freezes/resumes animation. **Clear** sends black.

Content can be previewed locally while disconnected. Native GIFs can continue
after disconnecting; the preview is an approximation, not LED readback. Games and
the seam demo still stream from the PC. Up to 1,000 decoded frames and 16 million
output pixels are retained in memory. To open media at startup, use
`python -m games.wall.app --media path/to/animation.gif --connect`.

## Connection behavior

All panels must connect and pass the existing 64×16 device check before any
content is uploaded. Each canvas version is cropped/rotated into per-panel RGB
PNGs and uploaded concurrently. The next canvas waits for every completion
reply. Newer content replaces unsent frames instead of creating a backlog.
Each panel has at most one upload pending. The wall uses Standard pacing with
no Windows throughput hints.

**Align panel timing (experimental)** is an optional way to reduce tearing at
the seam during movement. It is off by default. Enable it while playing to
compare: the controller measures each panel's upload duration, then starts
faster panels later so their completion replies should arrive closer together.
It needs at least three completed frames and uses the median of the latest
seven uploads to avoid chasing isolated slow replies. Delays are capped at
250 ms and apply to the same canvas version; the next version still waits for
all panels. Switching it off restores simultaneous submissions on the next
frame. Reconnecting starts with fresh measurements.

The status area shows the applied delays and **reply gap**. These measure host
completion timing, not when the LEDs actually change. Alignment may help when
one link consistently finishes earlier, but it cannot guarantee a seamless
display swap and may add some latency to the faster panel. If it looks worse,
turn it off. To start with alignment enabled:

```powershell
.\.venv\Scripts\python.exe -m games.wall.app --maze --align-timing --connect
```

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
Add `--align-timing` to compare the adjustment. Frame captures include each
panel's upload duration, actual start/completion offsets, requested delay and
completion gap. The diagnostic reports the median reply gap after warm-up.
