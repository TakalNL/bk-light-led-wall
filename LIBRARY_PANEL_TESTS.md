# Active panel research: upstream library tests

Date: 2026-11-14. User requested continued panel testing before application work:
larger/longer GIFs, power-cycle retention, better live-game performance and partial
updates. Both playback capacity and retention after unplugging are in scope.

## Current results

| Question | Verified result |
| --- | --- |
| Longer local playback | 4096 numbered frames, 1,915,364 bytes, encoded 204.8-second loop at 20 fps; owner confirmed all frames shown correctly |
| Retention without power | Original twenty-frame slot-1 GIF resumed automatically after an owner-performed power cycle |
| Faster live streaming | 3000/3000 compact RGB frames acknowledged over five minutes at scheduled 10 fps; owner confirmed final counter 3000 but was absent during playback; earlier 100-frame run visually confirmed |
| Partial changes | Same-session acknowledged coordinate add/erase preserved other pixel-drawn content; visibly sequential |
| Unsupported candidates | Four-bit indexed PNG displayed black; fast GIF and fast native-pixel animation visibly failed; pixel edits did not overlay PNG |

These are one-unit results. Capacity maxima, exact screen refresh and long-term
stability of the new 10 fps path are unmeasured. Replies alone do not prove rendering.

## Library and instrumentation

Installed the inspected local `pypixelcolor` checkout, version metadata 0.5.0,
commit `c8cbaebca6df7797a7bcface8a1c4ca33e499973`, into the project venv.
`examples/library_panel_tests.py` uses its actual PNG/GIF/pixel/slot builders,
`AckManager` and `send_plan`. No upstream source files were changed. Our adapter
provides the verified Windows cache/service settings, exact byte logging, bounds
and optional write pacing; this is not an unmodified public Client lifecycle test.
The clock query is assembled with the already-verified Berlin time to avoid
using the execution host's timezone; library response handlers parse its replies.

Important source findings:

- `send_plan(..., write_with_response=False)` is the library's documented fast
  transport; it still waits for each image window's application acknowledgment.
- `set_pixel` changes one coordinate and explicitly requires no application ACK.
- The Web Bluetooth reference's function named `updatePixels` constructs and
  sends a full raw framebuffer. It does not demonstrate a native rectangle upload.
- Persistent content uses `save_slot` and `show_slot`. The library warns that
  corrupted saved content can cause boot loops. Use only a tiny already-verified
  GIF for the initial retention test; no reset/clear command or bulk persistent
  capacity test is planned. The user has authorized testing retention.

## Completed findings so far

The same native 44-frame eyes file (20,500 GIF bytes) was submitted through the
library. Both normal and fast transmitted bytes were reconstructed and matched
the exact library plan, including both window headers and whole-file CRC.

- Normal acknowledged writes: final `0500030003`, upload completed in 3.811 s;
  no separate owner visual check before the next test.
- Unpaced fast writes: final `0500030003` in 0.422 s, **owner reported frozen at
  frame 002**. This is a visual failure, not a successful speed improvement.
- Paced acknowledged recovery, 10 ms per chunk and one-second connected settle:
  owner confirmed recovered normal motion and counter looping.
- Fast writes with the same pacing/settling: owner reported **frozen at frame 006**.
  Do not use fast GIF mode for persistent writes or call it verified on this unit.
- Second acknowledged recovery completed. The reported fast-write maximum was
  514 bytes at MTU 517, so 244 bytes was within the advertised limit. This does
  not establish the cause of the freezes; no firmware defect is inferred yet.
- A small known twenty-frame GIF was uploaded with 500-byte **acknowledged**
  chunks, within MTU and Bleak's documented 512-byte write-with-response limit.
  Owner confirmed normal looping through all twenty frames. Upload took 0.439 s.

The motion suite used 500-byte acknowledged PNG writes and the actual library's
individual `set_pixel` commands. Its transport results are:

| Phase | Completed / requested | Result |
| --- | --- | --- |
| Full PNG, 10 fps | 15 / 60 | Stopped when next start was 61 ms late |
| Full PNG, 20 fps | 1 / 80 | Stopped when next start was 60 ms late |
| Individual pixels, 5 fps, acknowledged | 40 / 40 | Eight-second run completed |
| Individual pixels, 20 fps, unacknowledged | 120 / 120 | Six-second submission run completed |

Full PNG uploads at 10 fps took 57–135 ms per frame (median 90 ms), so this
configuration did not maintain the requested schedule. Pixel motion changed four
coordinates on most steps and eight at wraparound. Acknowledged pixel steps took
167–196 ms; unacknowledged steps took 3.7–8.5 ms of host submission time. The final
ordered info query completed in 0.285 s after the fast pixel run, including the
library's notification subscription changes. This is not a display latency metric.
Owner reported **no recognizable motion comparison, only yellow pixels resembling
corruption**. Treat the suite as a visual failure; none of its phases has separate
visual confirmation. In particular, the host submission figures do not establish
usable partial animation or preservation of an uploaded PNG background. Whether
pixel writes select a separate drawing buffer/mode remains unresolved. Fast GIF
failures do not by themselves establish fast pixel behavior.

These failures directly demonstrate why the application completion notification
must not be treated as independent proof of correct GIF playback.

After the motion suite, the known twenty-frame GIF was restored with acknowledged
500-byte chunks and 10 ms pacing. Upload took 0.438 s; owner confirmed normal
playback had returned.

The 1024-frame capacity file then uploaded in 56.084 s, using 975 acknowledged
GATT writes over 39 application windows (38 intermediate replies, final status 3).
After disconnect and a 55-second observation period, the owner confirmed all 1024
frames and smooth playback. This establishes a working 479,139-byte file with an
encoded 51.2-second loop at 20 fps, not a hardware maximum. Actual screen timing
remains uninstrumented.

The 2048-frame upload was stopped at the owner's request to unplug the panel.
Its capture ends during write 200, without a final completion reply or visual
assessment. This is an **interrupted attempt**, not a capacity failure. The owner
then confirmed the panel was plugged in again, authorizing resumption. A fresh
attempt starts from the beginning in `lib-capacity2048-retry-20261114.jsonl`.

The retry completed: 958,185 GIF bytes, 78 application windows, 1,950 acknowledged
GATT writes, 77 intermediate status-1 replies and final status 3, in 105.544 s.
All captured image-write chunks matched the actual upstream plan byte for byte.
After disconnect and 106 seconds of observation, the owner confirmed all **2048
frames**. The encoded loop is 102.4 seconds at 20 fps. Thus both prepared capacity
files work; neither result establishes the hardware ceiling or power-cycle
retention. The large GIF used slot 0.

For retention, the original 4,088-byte twenty-frame sprite GIF was submitted to
slot 1 using 500-byte acknowledged chunks and 10 ms pacing. Its single message
differs from the verified slot-0 message only at header byte 14 (slot 0 to 1);
GIF payload and CRC are unchanged. Upload took 0.364 s in nine GATT writes and
returned final status 3. After disconnect, the owner confirmed normal looping
01/20–20/20. The owner has now been asked to remove USB power for five seconds,
restore it and describe the boot display before any further connection or write.
The owner confirmed that after the power cycle the panel showed its boot animation
and then automatically resumed our twenty-frame GIF. This establishes retention
and automatic startup selection for this slot-1 fixture after one power cycle;
it does not measure total persistent capacity or all slot-selection behavior.
No `show_slot`, clear, delete or reset command was needed.

## Limits still unmeasured

1. Hardware maximum file size/frame count and large-file persistent capacity.
   The successful 4096-frame result reaches this experiment's explicit bounds,
   not a demonstrated device limit. The ordinary examples keep their smaller bounds.
2. Longer-duration stability and exact physical timing of the compact 10 fps
   live path. The 15/20 fps scheduling stops are pipeline results, not a measured
   physical refresh limit. Fast native-pixel motion remains unsupported.
3. Reconnect drawing-state behavior, atomic rectangle updates, additional slots
   and repeatability on a second host/unit. The same-connection slow coordinate
   edits and one small slot-1 power-cycle test are the verified cases.

Prepared private capacity inputs:

- `captures/library-capacity-20261114/eyes-1024f-20fps.gif`: 479,139 bytes,
  39 windows, 1024 distinct numbered frames, encoded 51.2-second loop.
- `captures/library-capacity-20261114/eyes-2048f-20fps.gif`: 958,185 bytes,
  78 windows, 2048 distinct numbered frames, encoded 102.4-second loop.
- `captures/library-capacity-20261114/eyes-4096f-20fps.gif`: 1,915,364 bytes,
  156 windows, 4096 distinct numbered frames, encoded 204.8-second loop.

The eye motion repeats its 44 original frames; the four-digit counter makes
distinct decoded test frames. All three are visually confirmed. The first 2048-frame
attempt was interrupted at the owner's request; the fresh retry succeeded.

An optional `--indexed-png` probe is prepared for later live-update testing. It
uses a fixed sixteen-color PNG palette, preserving the scene's diagnostic colors
and reducing font antialiasing shades. All 300 numbered `PNG20` test frames remain
distinct after decoding; their entire framed messages are 311–346 bytes, fitting
one 500-byte acknowledged write. A static four-bit indexed PNG uploaded in one
acknowledged write, received final status 3 in 0.059 s, but the owner reported
**an entirely black panel**. This encoding failed its visual check; it is not a
supported live-image path. Other indexed bit depths were not tested.

A replacement `--pixel-hud` probe uses simple 3-by-5 bitmap text and keeps RGB
PNG encoding. All 300 distinct numbered test frames round-trip without pixel
changes and fit into 246–267-byte complete messages. The owner confirmed the
static RGB bitmap-HUD scene rendered correctly. A 100-frame, 10 fps live test
then completed in 10.011 s with one acknowledged write and expected image reply
per frame. The owner confirmed it looked very good, with intact background and
normal counter progression. Frame request/reply durations were 48.014–90.167 ms
(median 61.593); frame-start intervals were 91.755–110.788 ms, with maximum
schedule lateness 15.861 ms. This is a short verified improvement over 5 fps,
not a long-duration stability result or instrumented display-rate measurement.

At 20 fps the script deliberately stopped after frame 004: the next start was
30.583 ms late, exceeding its half-period cutoff of 25 ms. The owner independently
observed it stopped at 4. The capture contains `motion_stopped_late` followed by
normal disconnection/finish; this was not a Codex-limit interruption or an
observed autonomous panel freeze. At 15 fps, acknowledged writes reached frame
026 before the script stopped: frame 27 was 37.223 ms late, above the 33.333 ms
cutoff. The owner observed the same final frame. A single-write-per-PNG fast
transport comparison at 15 fps follows; per-image completion replies remain
required. This fast PNG test reached frame 018 before a scheduling stop: frame
19 was 43.610 ms late. The owner independently reported final frame 18. It did
not establish stable 15 fps, and no throughput improvement is claimed. Prior
fast GIF failures remain failures regardless of this PNG result.

The isolated static pixel-patch probe uploaded the verified RGB scene, waited
three seconds, then sent nine acknowledged `set_pixel` commands for a red 3-by-3
block at x30–32/y10–12. The owner saw **only the red block**, with no PNG border,
HUD or yellow square; they may have seen it build up one pixel at a time. Thus
pixel commands did not overlay the PNG on this unit. Separate buffer architecture
is a hypothesis, not established internals. Next, add a green block without any
image upload, then test erasing only the red block with black pixel writes.

The owner then pointed out that every connection flashes a Bluetooth indication
and resets the display. Thus the separate-connection green-add probe cannot
establish preservation across reconnects; its result must not be interpreted as
coordinate clearing. The PNG-to-red probe itself used one connection, so its
within-session observation stands. `examples/pixel_session.py` now keeps a single
connection open and waits for explicit local control-file commands between
supervised red/add-green/erase-red/baseline/motion stages. No reconnection occurs
between those observations. Each wait is bounded to ten minutes.

In that uninterrupted session the owner confirmed the red block, the green
addition, and then **red disappearing while green remained intact**. They noted
the visible one-pixel-at-a-time updates. This confirms coordinate drawing and
black erasure can preserve other pixel-drawn content within one session; it does
not establish an atomic rectangle operation or preservation across reconnects.
The acknowledged nine-command patches were sequential, so slow buildup is
expected. A complete native-pixel background was then drawn once, after which
only changed square/HUD coordinates were submitted for numbered motion.

The owner confirmed the full native-pixel background was correct, while noting
brief pauses during its acknowledged setup. Fast native motion then submitted
47 of 200 requested numbered frames before its scheduling stop (next frame
33.720 ms late). These frames required 474 coordinate writes, 5–36 per frame;
host submission durations were 4.596–82.762 ms, median 9.475 ms. The ordered query
afterward took 1.654 s including notification changes, suggesting transport delay
but not measuring screen timing. The owner reported **corruption during motion**.
This is a visual failure, not a verified 20 fps partial-update path. The same
connection stayed open through every stage, so reconnect display changes do not
explain this failure. The session was then ended and acknowledged GIF recovery
started. Keep fast pixel animation experimental/unsupported on this unit.
The owner confirmed the recovery GIF looped normally again.

A further capacity test is prepared within the existing bounds: 4096 frames,
1,915,364 bytes, 156 windows, encoded 204.8-second loop at 20 fps. SHA-256:
`1e50852e6f6ba396fb04f7839e5ad402d1d8607156d2810f786d6d61b49d3050`.
It uses the verified acknowledged slot-0 path; slot 1 remains unchanged. The
upload timeout is explicitly 360 s because the prior 958-KB transfer took 105.5 s;
the ordinary 180-second software timeout would be inappropriate for twice that
size. A 210-second disconnected observation follows a successful upload. Neither
the timeout nor the 2-MiB / 4096-frame experiment bounds are device specifications.
Upload completed in 216.759 s across 3,897 GATT writes, with 155 intermediate
status-1 replies and final status 3. Every captured image chunk exactly matched
the upstream plan. After the disconnected full-loop observation, the owner
confirmed **4096 frames shown correctly**. This establishes working playback of
this specific file, not a maximum. No instrumented screen timing was collected.
The 4096-frame slot-0 GIF was left playing; the small saved slot-1 GIF was not
overwritten. No further hardware tests are running.

## Five-minute RGB endurance follow-up

The owner subsequently requested a five-minute live RGB test at 10 fps. The
runner now supports up to 3000 frames only for acknowledged RGB streaming at
10 fps with the bitmap HUD. The four-digit counter is 0001–3000, and the final
frame is labelled END. All 3000 generated RGB frames were decoded in an offline
test: each is distinct, preserves the border/corners and fits in one 500-byte
acknowledged write. Eight targeted library tests pass after this extension.

The hardware run uses the same upstream builder/transport, one continuous
connection, slot 0, no retries and no additional chunk delay. It retains the
absolute schedule and 50-ms maximum start lateness; a cutoff stop or bad reply
is a failed endurance attempt, even if the process exits normally. Planned
duration is 300 seconds, 3000 expected image replies. Raw capture:
`captures/lib-rgb-10fps-five-minute-20261114.jsonl`.

Transport result: **3000/3000** frames and strict expected PNG replies in
**300.015648 s** (9.99948 fps), one uninterrupted connection, no retry, cutoff or
reported error. Every complete image message was 248–275 bytes and used one
acknowledged GATT write. The final RGB frame reads END 3000. The owner confirmed
the display was on counter 3000, but was absent during the run. This establishes
final-frame rendering in addition to the five-minute transport pass; continuous
visual smoothness, absence of transient corruption and display of every
intermediate frame remain unverified. No repeat hardware test was started.

| Metric | Result |
| --- | --- |
| Frame request/reply min / median / max | 47.748 / 60.853 / 125.348 ms |
| Frame request/reply p95 / p99 | 84.658 / 94.537 ms |
| Frame-start interval min / median / max | 75.311 / 94.024 / 125.405 ms |
| Maximum schedule lateness | 28.806 ms, below the 50-ms cutoff |

Frame-start intervals describe host scheduling; physical display timing remains
uninstrumented. Summary is in the private capture sidecar. Full software suite
after this runner extension: **132 tests passed**, including all 3000 four-digit
RGB frame round-trips, unchanged border/corners and single-write size checks.

Latest automated result: 132 tests passed, including actual upstream builder
parity, traced fast transport, four-digit capacity preparation and partial
coordinate updates that preserve the scene outside the ball strip. No software
test uses hardware. Current hardware evidence remains in private `captures/`.

## Backend consolidation check — 2026-11-16

All game and experiment writes now share the pinned pypixelcolor builders,
`AckManager` and `send_plan`. The separate experimental request manager,
PNG/GIF encoders and chunk loop were removed. The adapter retains bounded
connections, Windows cache settings, tracing, strict reply/profile checks and
explicit clock timezones. Device mappings and pixel/time command building are
delegated to upstream. The failed raw-RGB reference remains a negative-test
fixture, not a supported display path. At this consolidation checkpoint the public
client lifecycle was still untested; the subsequent successful small-file
`AsyncClient` trial is documented in [PUBLIC_CLIENT_TESTS.md](PUBLIC_CLIENT_TESTS.md).

The first sandbox attempt discovered the known panel at -69 dBm but failed to
open its connection before any application writes. A fresh Windows host attempt
connected successfully with cached FA services, MTU 517 and -68 dBm:

- The diagnostic RGB PNG labelled `LIB` used a 304-byte application message,
  two acknowledged writes and the expected `0500020003` completion reply in
  134.548 ms.
- A separate fresh host connection uploaded the original 4,088-byte, twenty-frame
  numbered GIF to non-saving slot 0. Its 4,103-byte message used seventeen
  acknowledged writes and received `0500030003` in 764.621 ms. The connection
  closed before the twelve-second observation period.
- The owner confirmed both the bordered `LIB` image and numbered GIF playback
  looked correct, including looping after disconnect. Physical timing was not
  instrumented. The saved slot-1 startup animation was not overwritten.

Private captures: `captures/cleanup-static-20261116.jsonl` (failed sandbox
attempt), `captures/cleanup-static-host-20261116.jsonl` and
`captures/cleanup-gif-host-20261116.jsonl`. Preview PNG/GIF files have matching
names. No further hardware tests are running; the slot-0 GIF is left playing.

Software validation: 164 hardware-free tests passed, covering immediate replies,
unrelated notifications, MTU chunking, multi-window ACKs, partial-write failures,
cancellation, capture errors and rejection of unknown/malformed profiles. All
ten example and three game command-help checks passed, as did hidden-window
start/reset checks for all three game previews. The editable package and wheel
rebuilt successfully; dependency checks passed. Non-test Python decreased from
3,314 to 3,017 physical lines (including comments and blank lines), a net
reduction of 297 lines.

## Later public-client fast PNG follow-up — 2026-11-16

[FAST_MODE_TESTS.md](FAST_MODE_TESTS.md) records a later comparison through the
public client with configurable chunks from PR #90. A fully watched two-minute
fast RGB PNG stream completed all 1,200 updates at 10 fps, with correct rendering
confirmed by the owner. At a requested 15 fps, fast mode averaged 11.188 fps and
the acknowledged control 10.863 fps; the owner reported occasional brief pauses
or missing frames in both. Neither sustained 15 fps, and no convincing fast-mode
advantage was established. This adds a verified small-PNG case, while the earlier
fast GIF and native-pixel failures remain unresolved. All tests are finished;
the panel is now left at `END 1304`, not the earlier recovery GIF.
