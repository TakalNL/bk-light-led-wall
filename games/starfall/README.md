# STARFALL: side-scrolling space shooter

Double-click **Start Starfall.cmd**. It opens ready and uses the last panel
selection from Snake. Connect the panel, click the preview, then press Enter.
Only one game should hold the panel connection at a time; disconnect or close
Snake before connecting Starfall.

## Controls

- **Enter:** launch / pause / resume. **P / Escape:** pause (P also resumes).
- **Arrow keys / WASD:** hold to move. The ship stays on the left side.
- **Space:** hold to fire. The **Auto-fire** checkbox fires continuously instead.
- **R / New game:** reset to three lives; Enter starts the next run.
- Losing focus or the panel connection pauses play. **Play on PC only** supports
  local play without Bluetooth. Click the preview to return keyboard focus.

## Campaign

Three finite waves contain eighteen enemies before the carrier arrives. Fast
green **drones** fly straight (1 HP, 100 points). Magenta **weavers** move up and
down (2 HP, 180 points). Orange **gunners** fire aimed orange projectiles (3 HP,
250 points). Escaped enemies award no points. The boss appears after the last
wave has been cleared or passed; it has 96 HP, a panel health bar and faster,
wider projectile fans below half health. Defeating it ends the campaign and
awards 1500 points plus 250 per remaining life.

Cyan **T** capsules permanently unlock **twin cannons**. Yellow **R** capsules
permanently unlock **rapid fire** (0.35-second cooldown becomes 0.15 seconds).
Fly into a capsule to collect it. Scheduled supply drops arrive aligned with
the ship around ten and twenty-seven seconds into the campaign; destroyed
gunners can also drop missing upgrades. Capsules drift left and can be missed.
Upgrades survive life loss and reset for a new campaign.

You have **three lives**. Enemy contact or an enemy shot consumes one life.
Every hit shows **HIT, points and remaining lives on the panel** for 1.8 seconds,
then respawns the ship with 2.5 seconds of blinking protection. The campaign
pauses during that interstitial. At zero lives, the panel holds **OUT / PTS / L0**.
After the boss, it holds **WIN / PTS / remaining lives**. Points and lives also
remain visible in the PC window. During play, cyan dots at the upper left show
lives; lower-left cyan/yellow dots show collected upgrades.

## Display and implementation

Original pixel sprites and a scrolling starfield render directly into a 64×16
RGB image. The PC game runs a fixed 20-Hz simulation; panel output uses the
acknowledged PNG path capped at ten uploads per second by default. The optional
[Windows profile](../common/README.md#panel-update-profiles) targets twelve. One image is
in flight; older unsent states are replaced. The PC preview is the current game
state, not a camera or readback of the LED panel. A delayed frame does not stop
the game; a failed image reply or disconnect pauses it without automatic retry.
The saved startup GIF is not overwritten.

This uses the shared desktop shell and panel worker in `games/common/`, with separate game rules,
renderer, controls and logs (`captures/starfall-*.jsonl`, `starfall-errors.log`).
It needs the same optional `game` dependencies described in [Snake README](../snake/README.md).

Run these commands from the repository root:

```powershell
.\.venv\Scripts\python.exe -m games.starfall.app --connect
# Local-only game:
.\.venv\Scripts\python.exe -m games.starfall.app --preview
```

Tests cover all enemy behaviors, firing upgrades, supply collection, scoring,
three-life handling, respawn immunity, pause, boss gating/attacks/victory, result
screens and a complete scripted campaign. The coverage campaign uses test-only
invulnerability; a separate automated pilot also completed a normal campaign
with three lives, both upgrades and 5430 points in 57.7 campaign seconds. This is
not a watched human-play result. Sampled simulation frames stayed within one
500-byte write (normal pilot maximum 316 bytes). Keyboard controls were exercised
in a hidden window, and the original Snake shell was checked after sharing its
transport/UI. The full suite passed 155 tests; the final targeted game checks
passed 23. The initial Starfall ready image (221 bytes) was acknowledged by the
owner's panel in about 62 ms. The owner subsequently confirmed the game prototype works. A watched complete
hardware campaign and measured input-to-display latency remained unverified at
that checkpoint.

A later [two-minute scripted streaming comparison](../../STARFALL_STREAM_TESTS.md)
used normal game rules and controls through both transports. The public
`AsyncClient` completed 1,175/1,200 scheduled updates (9.78 fps); the current
adapter completed all 1,200 at 10 fps. The owner confirmed both looked correct
with little visible difference. A later local public-client patch exposed
`chunk_size=500` and also completed all 1,200 updates, with correct rendering
confirmed. Games retain the adapter's lifecycle bounds and diagnostics pending
integration. These replays used pre-rendered game frames and do not measure
interactive keyboard-to-display latency.
