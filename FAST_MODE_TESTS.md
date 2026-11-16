# Public-client fast-mode tests — 2026-11-16

Fast-mode small RGB PNG streaming passed a fully watched two-minute 10-fps run.
At a requested 15 fps, fast and acknowledged writes both completed roughly 11
updates per second, and the owner noticed occasional brief freezes or missing
frames in both. There is no convincing speed advantage for this workload. Keep
acknowledged writes as the game default; these results do not rehabilitate the
earlier fast GIF or native-pixel failures.

## Method

The public-client runner compares acknowledged BLE writes with
`write_with_response=False`, using the local pypixelcolor checkout at PR #90
commit `cfbc7bd0cb392bb499ee35c8cc9dce40cd2c8893`. It requests 500-byte chunks
through the public constructor; unacknowledged writes are additionally capped by
the characteristic limit. The upstream builders, send loop and notification/ACK
handling are unchanged. The app's production adapter and defaults are unchanged.

Each game image is a native 64x16 RGB PNG, sent to non-saving slot 0. There is
one upload in flight and exactly one required `0500020003` completion reply per
image. The schedule selects the latest source state after an overrun rather
than queuing old states. Thus skipped source states do not establish dropped LED
frames. END is a separate final image excluded from streaming timings/counts.

Fast mode removes the GATT response wait for each write; it still waits for
image completion. A successful reply alone does not establish correct display
output. Owner observation is recorded separately.

The runner now accepts `--fast` and `--fps 10|15|20`. The game continues its normal
20-Hz simulation at every output rate. A regression check confirms that 10 fps
produces the exact previous sequence, with SHA256
`a660c92240c61aa890cc2234fa0f01c415253ef7e368dfbad5708468cec97e44` for 120 seconds.
It also checks 15-fps sampling duration/game progression and scheduling at all
three rates. All 171 application tests pass against original and patched library
imports; invalid fast/adapter combinations are rejected before connecting.

## Two-minute 10-fps comparison

Both runs used the same 1,200 pre-rendered images and the SHA256 above. PNG sizes
were 142–307 bytes (157–322 with image framing). Only the public write-response
setting changed; connection options remained upstream defaults. The trials were
sequential on the same Windows host/panel, not randomized repeated measurements.

| Metric | Acknowledged, requested chunks 500 | Fast, requested chunks 500 |
| --- | ---: | ---: |
| Scheduled updates | 1,200 | 1,200 |
| Completed uploads with strict replies | 1,193 | 1,200 |
| Skipped source states | 7 | 0 |
| Stream elapsed time | 120.004 s | 120.013 s |
| Achieved upload rate | 9.941 fps | 9.999 fps |
| Upload/API time, median | 79.676 ms | 80.622 ms |
| Upload/API time, p95 | 108.969 ms | 101.875 ms |
| Upload/API time, maximum | 270.152 ms | 134.929 ms |
| Final marker | `END 1193` | `END 1200` |

The first fast attempt failed during discovery, before connection or any image
writes. A separate targeted scan then found the panel advertising; a fresh
public-client retry completed the fast run above. This was not a fast-image
timeout or observed rendering failure. The retry still used upstream connection
defaults. The discovery failure and intervening scan are part of the test history.

Both completed sessions disconnected cleanly, without an in-stream reconnect.
Debug logs contain 1,194 and 1,201 strict PNG replies, including the END markers.
The owner reported correct output during the portion they watched, but did not
watch the whole fast run and requested a repeat. The full run therefore lacks
complete visual observation. The median upload time barely changed; these
measurements do not demonstrate a substantial speed improvement.

Private captures:

- `captures/public-fast-ack500-10fps-120s-20261116.jsonl`
- `captures/public-fast-noresponse500-10fps-120s-20261116.jsonl` (discovery failure)
- `captures/public-fast-noresponse500-10fps-120s-20261116-r1.jsonl` (completed run)

Each has a `.debug.log` sidecar. Raw logs can contain unique Bluetooth identifiers
and remain private.

## Repeated two-minute fast run

At the owner's request, the same fast-mode 10-fps run was repeated so they could
watch its full duration. The source SHA256, 500-byte request, public API and
non-saving slot remained unchanged. The run completed all 1,200 images, skipped
none and disconnected cleanly. There were 1,201 strict completion replies,
including the separate `END 1200` marker.

Stream duration was 120.015 seconds (9.999 fps). Upload/API times were 82.955 ms
median, 103.756 ms p95 and 138.140 ms maximum. The owner confirmed they watched
the full run and it stayed correct throughout. This verifies two-minute playback
of this small-PNG workload at 10 fps on this panel. The private capture is
`captures/public-fast-noresponse500-10fps-120s-20261116-watched-repeat.jsonl`, with
its debug sidecar.

## Two-minute 15-fps comparison

After the owner confirmed the complete 10-fps repeat, the runner first tried fast
mode at 15 fps and then acknowledged writes at the same rate. Both used the same
1,800 native RGB PNGs, requested 500-byte chunks, upstream connection defaults
and non-saving slot 0. PNG sizes remained 142–307 bytes. The normal game simulation
ran at 20 Hz; the higher output rate did not speed up the game. The concatenated
input SHA256 for both runs was
`1839405046f3140022ee5b9f1431779aed4a91228370354c1b5b55b40fa783c1`.

| Metric | Fast, requested chunks 500 | Acknowledged, requested chunks 500 |
| --- | ---: | ---: |
| Scheduled updates | 1,800 | 1,800 |
| Completed uploads with strict replies | 1,343 | 1,304 |
| Skipped source states | 457 | 496 |
| Stream elapsed time | 120.037 s | 120.037 s |
| Achieved upload rate | 11.188 fps | 10.863 fps |
| Upload/API time, median | 89.894 ms | 89.919 ms |
| Upload/API time, p95 | 112.358 ms | 112.489 ms |
| Upload/API time, maximum | 134.929 ms | 135.258 ms |
| Final marker | `END 1343` | `END 1304` |

Every completed upload received its strict final reply. There were 1,344 and
1,305 strict replies including the separate END markers. Both sessions finished
and disconnected cleanly, without a reconnect during streaming. The owner
reported possible small freezes or missing frames and explicitly confirmed they
noticed them in **both** runs. This is an observation of uneven presentation,
not proof of image-payload corruption, lost BLE packets or an autonomous freeze.
The sender's measured scheduling skips are consistent with this observation,
but individual visible pauses were not matched to timestamps.

Fast mode completed about 3% more uploads in this pair, with essentially the
same median/p95 API times. Neither path sustained the requested 15 fps; about
25% and 28% of scheduled source states were skipped. One sequential pair on one
host/panel is insufficient to establish a reliable speed advantage. These
end-to-end API timings do not isolate firmware decoding, connection scheduling,
host latency or physical display refresh as the cause.

Private captures, each with a debug sidecar:

- `captures/public-fast-noresponse500-15fps-120s-20261116.jsonl`
- `captures/public-fast-ack500-15fps-120s-20261116.jsonl`

No 20-fps run was attempted after both 15-fps modes missed the requested rate and
showed visible stutter. No hardware test remains running. The panel is left at
`END 1304` from the acknowledged control. The production game transport remains
acknowledged with its existing 10-fps target.

## Limits and previous failures

This comparison only exercises small complete PNG uploads. Earlier fast GIF
uploads visibly froze despite final success replies, and fast native-pixel motion
visibly corrupted. An earlier fast PNG test at 15 fps hit its scheduling cutoff;
that stop did not establish a panel freeze. These findings remain qualified as
recorded in [LIBRARY_PANEL_TESTS.md](LIBRARY_PANEL_TESTS.md).

No persistent writes, new fast GIF uploads or pixel animation were performed in
this comparison. Correct PNG playback would not establish that fast transport is
reliable for those other workloads. No findings have been added to PR #90.

## Reproduction

Use a new capture filename per run:

```powershell
$env:PYTHONPATH = "$PWD\.research\ipixel-chunk-size\src"
.\.venv\Scripts\python.exe examples\public_game_stream.py $deviceId --chunk-size 500 --fps 10 --seconds 120 --output captures\ack10-new.jsonl
.\.venv\Scripts\python.exe examples\public_game_stream.py $deviceId --chunk-size 500 --fps 10 --seconds 120 --fast --output captures\fast10-new.jsonl
Remove-Item Env:PYTHONPATH
```

Wait for owner confirmation of correct rendering before advancing the rate.

A later [throughput-profile comparison](WINDOWS_TRANSPORT_PACING_TESTS.md)
again found no speed advantage from fast PNG writes: 12.89 uploads/second
versus 13.06 with acknowledged writes at a requested 15 fps. The owner watched
the fast run and confirmed correct rendering throughout. This only covers
small complete PNGs and leaves the prior fast GIF/native-pixel failures open.
