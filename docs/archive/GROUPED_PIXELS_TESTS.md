# Grouped-pixel Snake experiment

This experiment checks whether sparse game updates can exceed the roughly
11 complete PNG uploads per second observed on this Windows host and panel.
It uses the proposed upstream `set_pixels` builder from
[pypixelcolor PR #88](https://github.com/lucagoc/pypixelcolor/pull/88), pinned to
`fff5cc7ff44e318eb40d114a387574dca7de8d1d` in the isolated
`.research/ipixel-set-pixels` checkout. The app's installed dependency and game
transport are unchanged. The user-approved static compatibility confirmation
and typical command-count reduction were
[posted on PR #88](https://github.com/lucagoc/pypixelcolor/pull/88#issuecomment-6921610979).
The motion benchmark and unresolved tail-gap observations have not been posted.

## Method

`examples/grouped_snake_stream.py` runs a deterministic Snake pilot with normal
turns, collisions, food and growth. Each requested update advances one game
move; the 15-fps workload therefore moves faster than the interactive game's
ordinary setting. It is a transport benchmark, not a human-input test.

Changed coordinates are grouped by their destination RGB colour, with at most
123 coordinates per upstream command. A normal move changes twelve LEDs in
three commands, rather than twelve individual pixel commands. If the host
misses a scheduled update, it computes the next difference against the last
fully sent image, so skipped states do not leave an old tail behind. Every new
connection begins with an explicit full framebuffer, including black pixels.

Both modes use the existing Windows connection adapter and acknowledged GATT
writes, with one command in flight. Native pixel commands have no application
completion reply: their timing measures host-side write completion, not physical
display refresh. The three colour groups also do not form an atomic frame.
The PNG control waits for each strict image completion reply. An ordered device
query after motion can expose queued transport work but is not a render fence.
The final END marker uses an acknowledged, non-saving PNG in slot 0.

No persistent slots, reset or factory-clear commands are used.

## Static probe, 2026-11-16

The full 64x16 probe used fourteen grouped commands for all 1,024 coordinates.
The owner confirmed the black background, coloured L-shaped corner markers
(red top-left, green top-right, blue bottom-left, yellow bottom-right), and eight
white dots across the middle were all correct. The session then disconnected
cleanly. Private evidence:
`captures/grouped-pixels-probe-20261116.jsonl` and its expected PNG/debug sidecars.

## Motion results

The first run requested 900 Snake updates at 15 fps. It completed 407 updates
and skipped 493 source states in 60.097 seconds: **6.772 updates/second**. This
is host-side GATT completion throughput, not a measured display refresh rate.
The 1,227 grouped commands took 135.777 ms per update at the median, 179.968 ms
at p95, and 225.015 ms at maximum. The final ordered query took 247.477 ms;
the strict PNG END marker succeeded and the session disconnected cleanly.
The final score was six. The owner said motion looked pretty fast, but the tail
was not always smooth and there appeared to be a gap between its last two
pixels. This is not an intended visual effect. An offline check of every one
of the 900 source images confirmed adjacent body cells, with all four LEDs lit
in each cell. Native motion is therefore **not visually verified as correct**.
The cause of the observed gap remains unresolved; intermediate drawing across
separate commands is one possibility, not an established diagnosis.

Private capture: `captures/grouped-snake-ack-15fps-60s-20261116.jsonl`, with its
debug sidecar. The initial image and 900 raw RGB source states have concatenated
SHA256 `947d256a3fac61d0b9ef6bafc34d899cabe49804e8190b501684537535a5fe97`.

The equivalent PNG control used the same source hash and completed 646 of 900
updates in 60.030 seconds: **10.761 updates/second**. It skipped 254 source states.
Both runs requested 15 fps, used the same isolated upstream checkout, and
disconnected cleanly without stream errors. Neither sustained the requested
rate. The timings have different completion semantics, as described above.

| Metric | Grouped pixels | Complete PNG |
| --- | ---: | ---: |
| Completed updates | 407 | 646 |
| Skipped source states | 493 | 254 |
| Completed updates/second | 6.772 | 10.761 |
| Update time, median | 135.777 ms | 89.996 ms |
| Update time, p95 | 179.968 ms | 112.581 ms |
| Update time, maximum | 225.015 ms | 135.215 ms |
| Motion commands | 1,227 | 646 |
| Ordered query after motion | 247.477 ms | 225.084 ms |
| Final marker | END 407 | END 646 |

All 648 PNG uploads in the control (initial image, 646 motion images and END)
received exactly one strict completion reply. The grouped run's separate PNG
END marker also received its strict reply; its paint commands expect none.
Every attempted write in both captures completed with GATT response enabled.
The PNG control capture is
`captures/png-snake-ack-15fps-60s-20261116.jsonl`, with its debug sidecar.
The owner also saw the tail gap during the PNG control. It is therefore not
specific evidence against grouped-pixel commands, and neither motion run has
unqualified visual confirmation. Both streams skip scheduled source states,
which can make movement uneven, but the observation was not timestamp-matched
to those skips. Source-frame gaps have been excluded; the physical presentation
cause remains unresolved. No claim of payload corruption is established.

Smaller packets alone did not improve throughput in this pair: each grouped
update still required three or occasionally four sequential acknowledged
writes, whereas each complete PNG fit in one write. The result is consistent
with per-write latency dominating byte count, but it does not isolate the host,
Bluetooth scheduling or firmware as the cause. Keep the production transport
and its acknowledged 10-fps default. Further work would need to reduce write
round trips or change the connection behaviour, with fresh visual validation.
Those two motion runs did not test fast grouped writes, command concatenation,
concurrent uploads or another host's Bluetooth stack. The subsequent static
concatenation probe is recorded below.

After this comparison the panel was left at END 646 and both sessions were
disconnected. The next experiment is described below.

## Experimental command concatenation

The next hypothesis is that multiple complete native pixel commands might fit
inside a single acknowledged GATT write. This would reduce write round trips
without changing each upstream-generated command. Firmware support has not
been established from documentation, so this is gated on a static probe.
Transport acceptance alone does not establish that all commands were drawn.

The optional `batch-probe` mode first paints the entire background black using
separate verified pixel commands. It then sends three upstream commands in one
120-byte acknowledged write: sixteen blue coordinates, sixteen green, and
sixteen red. The expected picture has three 4x4 blocks: red on the left, green
in the middle, and blue on the right. Checking all three colours distinguishes
full parsing from accepting just the first command. The probe waits for owner
inspection before recovery with a complete acknowledged PNG and disconnect.
Private capture: `captures/batched-pixels-probe-20261116.jsonl`.

`pack_pixel_commands` preserves complete command bytes and boundaries and
rejects commands that exceed the negotiated write budget. The paint path
accepts only reply-free upstream native paint plans. Combined payloads are
bounded to the adapter's negotiated chunk size so the library sends each in
one write. No app transport, upstream checkout or published PR is changed.
The unvalidated batched motion mode was removed after the static probe failed.

### Result: only the first command was visible

The owner reported only a blue square. Blue was the first of the three commands
in the 120-byte payload; green and red were subsequent commands. The entire
write completed with GATT response enabled in 28.563 ms, but the owner did not
see the expected complete pattern. Concatenating complete commands this way
therefore fails the visual compatibility check on this panel. No batched motion
run or FPS claim followed. This is an unsupported framing experiment, not an
identified defect in the upstream `set_pixels` implementation.

The probe's ten-minute observation wait expired before its control file was
advanced. The logged `TimeoutError` is that host-side wait expiring, not evidence
of a panel freeze or failed write. A separate recovery connection uploaded the
complete three-colour pattern through the verified non-saving PNG path. It
received exactly the strict reply `0500020003` and disconnected cleanly. Private
recovery capture: `captures/batched-pixels-probe-recovery-20261116.jsonl`.
The recovery image has not received a separate owner visual confirmation.
No hardware test is running.

## Verification

The unchanged dependency passes 176 app tests, with four optional upstream
builder tests skipped. Selecting the PR #88 checkout passes all 180 app tests;
the upstream checkout's own 53 tests also pass. Focused tests reconstruct full
and differential images, including skipped source states, enforce the upstream
coordinate cap, and verify the actual upstream builder's command output.
Batch tests check preservation of command order and boundaries, rejection of
invalid payloads, and reconstruction of all three probe colours with budgets
requiring one, two or three writes. These checks do not emulate firmware support.

## Reproduction

Use fresh capture and control filenames. Keep each probe connected until its
picture has been checked, then write `finish` to its control file. Confirm
correct rendering before increasing the motion rate.

```powershell
$env:PYTHONPATH = "$PWD\.research\ipixel-set-pixels\src"
.\.venv\Scripts\python.exe examples\grouped_snake_stream.py $deviceId --mode probe --output captures\grouped-probe-new.jsonl --control captures\grouped-probe-new.control
# From a second terminal, after visual inspection:
Set-Content captures\grouped-probe-new.control finish
.\.venv\Scripts\python.exe examples\grouped_snake_stream.py $deviceId --mode grouped --fps 15 --seconds 60 --output captures\grouped-snake-new.jsonl
.\.venv\Scripts\python.exe examples\grouped_snake_stream.py $deviceId --mode png --fps 15 --seconds 60 --output captures\png-snake-new.jsonl
Remove-Item Env:PYTHONPATH
```
