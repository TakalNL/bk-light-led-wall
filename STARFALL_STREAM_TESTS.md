# Starfall streaming comparison — 2026-11-16

**Both paths rendered correctly, with little visible difference reported by the
owner. The default public client averaged 9.78 fps; the existing adapter completed
every scheduled update at 10 fps. A later public-client chunk-size patch also
completed all updates at 10 fps; see the controlled comparison below.**

## Workload and method

The runner [examples/public_game_stream.py](examples/public_game_stream.py) renders
two minutes of Starfall at its normal 20-Hz simulation rate and samples 1,200
RGB PNG frames at 10 fps. A deterministic pilot uses normal movement/firing
controls and ordinary game rules, including collisions and life loss. It uses
no invulnerability. The source sequence covers all three enemy types, both
upgrades, a respawn, carrier fights and wins. It is a scripted replay, not a
human-controlled desktop play test.

Both runs used the same pre-rendered PNG sequence, confirmed by its SHA256:
`a660c92240c61aa890cc2234fa0f01c415253ef7e368dfbad5708468cec97e44`.
Inputs were 142–307 bytes per PNG, or 157–322 bytes with upstream image framing.
All images were native 64×16 RGB. Rendering happened before connection, so the
timings measure upload/API work, not live rendering or keyboard-to-LED latency.

There was one upload in flight. Absolute 100-ms slots selected the latest source
state when a previous upload overran; skipped states were counted and never
queued for catch-up. A late reply is not evidence of a physically dropped LED
frame. Each completed upload had exactly one `0500020003` reply, observed through
upstream's debug logger without replacing its BLE callbacks or ACK handling.

- **Public path:** unmodified pinned `pypixelcolor.AsyncClient(address)` and
  `send_image_hex(..., '.png', save_slot=0)`, default acknowledged writes and
  244-byte chunks, no forced cache options, service filters or added pacing.
- **Adapter path:** the current `library_link.py` backend, upstream builders,
  ACK manager and send loop, cached FA-service settings and 500-byte acknowledged
  chunks. It does not add a chunk delay for games.

The trials were sequential on the same Windows host and panel. They were not
randomized repeated trials and do not isolate chunk size from every other
adapter/API difference. Both used non-saving slot 0; the saved startup GIF was
not overwritten. No application or upstream production code was changed.

## Results

| Metric | Public AsyncClient | Current adapter |
| --- | ---: | ---: |
| Scheduled updates | 1,200 | 1,200 |
| Completed uploads with strict replies | 1,175 | 1,200 |
| Skipped source states | 25 | 0 |
| Stream elapsed time | 120.105 s | 120.015 s |
| Achieved upload rate | 9.783 fps | 9.999 fps |
| Upload/API time, median | 64.580 ms | 61.766 ms |
| Upload/API time, p95 | 112.811 ms | 88.851 ms |
| Upload/API time, maximum | 179.887 ms | 112.886 ms |
| Start interval, minimum / median / maximum | 66.863 / 107.347 / 179.981 ms | 85.532 / 93.886 / 114.843 ms |
| Connection errors, retries or reconnects during streaming | 0 | 0 |
| Final diagnostic marker | `END 1175` | `END 1200` |

The END marker was a separate final upload, excluded from streaming counts and
timings. Debug logs contain 1,176 and 1,201 strict PNG completion replies
respectively, including these markers. Both sessions disconnected successfully.

The owner described the public run as correct and reasonably smooth, and the
adapter run as also correct with little visible difference. This is visual
evidence of the game presentation, not an instrumented check of every LED frame
or input latency. The source sequence ends with a win at 5,180 points and two
lives; the panel is left showing `END 1200`. No further tests are running.

## Interpretation

The default public client works for sustained game-frame uploads on this unit.
It did not complete every 10-fps slot in this run: 25 of 1,200 source states
were skipped, about 2.1%. The adapter had more timing headroom on the same clip.

Of the public run's completed images, 972 fit one default 244-byte write and 203
required two. Their median API times were 61.474 ms and 112.436 ms respectively.
Every source image fits one 500-byte adapter write. The measurements are
consistent with extra acknowledged-write round trips contributing to overruns;
this paired trial does not establish chunk size as the sole cause. It does not
measure a physical panel refresh-rate ceiling.

Retain the thin adapter's game transport settings until an alternative preserves
the application's timing, bounded operations, profile checks and diagnostics.
The successful public API remains useful for simpler content workflows. Larger
public-API uploads, other games, failure recovery and other hosts/units still
need their own evidence.

## Reproduction and validation

```powershell
.\.venv\Scripts\python.exe examples\public_game_stream.py $deviceId --seconds 120 --output captures\public-starfall-new.jsonl
.\.venv\Scripts\python.exe examples\public_game_stream.py $deviceId --backend adapter --seconds 120 --output captures\adapter-starfall-new.jsonl
```

Private captures are `captures/public-starfall-120s-20261116.jsonl` and
`captures/adapter-starfall-120s-20261116.jsonl`, plus their `.debug.log` sidecars.
Keep debug logs private because they can contain unique Bluetooth identifiers.

Four hardware-free benchmark checks cover the normal pilot's campaign/frame
properties, a complete on-time schedule, latest-state selection on a slow link,
and rejection of nonfinal replies. The full suite passed 168 tests, and all
twelve example command-help checks passed.

## Public chunk-size patch comparison

A separate local checkout at the same pinned commit now exposes optional
`chunk_size` configuration through both public clients. The patch and application
instructions are in [patches/README.md](patches/README.md). The original library
checkout, app dependency and production adapter remain unchanged. The focused
library patch has since been published as
[pypixelcolor PR #90](https://github.com/lucagoc/pypixelcolor/pull/90).

Two further sequential trials used this same patched checkout and the same
1,200 PNGs and SHA256 above. The first used `AsyncClient(address)` with unchanged
per-command defaults; the second used `AsyncClient(address, chunk_size=500)`.
Both used upstream connection defaults, acknowledged writes and the public
`send_image_hex` API. Only the chunk-size setting changed. No adapter, private
attribute override, cache option, service filter or extra pacing was used.

| Metric | Patched public, default 244 | Patched public, explicit 500 |
| --- | ---: | ---: |
| Scheduled updates | 1,200 | 1,200 |
| Completed uploads with strict replies | 1,175 | 1,200 |
| Skipped source states | 25 | 0 |
| Stream elapsed time | 120.105 s | 120.003 s |
| Achieved upload rate | 9.783 fps | 10.000 fps |
| Upload/API time, median | 65.649 ms | 64.013 ms |
| Upload/API time, p95 | 112.602 ms | 90.951 ms |
| Upload/API time, maximum | 157.629 ms | 136.308 ms |
| Connection errors, retries or reconnects during streaming | 0 | 0 |
| Final diagnostic marker | `END 1175` | `END 1200` |

Each upload and final marker produced exactly one strict PNG completion reply;
the debug-log counts were 1,176 and 1,201. Both sessions disconnected cleanly.
The owner confirmed both rendered correctly with little visible difference.
The display was left showing `END 1200`; no further tests are running.

This comparison supports configurable acknowledged chunks as an upstream feature:
the public client matched the adapter's completed-frame count without adopting
the adapter's connection settings. It reduced p95 API time by about 19.2% on
this workload. All framed images fit a single 500-byte write. This remains one
sequential pair on one Windows host/panel, not randomized repeated trials or a
cross-platform result. It does not establish performance for larger uploads,
other games or lower-MTU links, nor justify changing the library's default.

The patch adds validation, documentation, public stubs/generator signatures and
28 regression cases. All 68 library tests pass. All 168 application tests pass
against both the original and patched imports. The runner accepts
`--chunk-size 500`, rejects invalid values/adapter combinations before connecting,
and records the library import path and selected option. The original dependency
still imports normally unless `PYTHONPATH` explicitly selects the new checkout.

Private captures are
`captures/public-starfall-patched-default-120s-20261116.jsonl` and
`captures/public-starfall-patched-chunk500-120s-20261116.jsonl`, with debug sidecars.
The patch has been checked with `git apply --check` against the original clean
pinned checkout. Keep the adapter until its lifecycle bounds, profile checks and
diagnostics have an equivalent public-client integration; this result only
addresses the chunk-size setting.
