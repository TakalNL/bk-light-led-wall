# Native-size art: local playback rate and frame capacity

Date: 2026-11-14. Same reported two-metre desk position, separate USB supply,
PC antennas and cached FA-service layout. The owner requested both smoother
playback and more frames, using nicer online art before building a general uploader.

The selected yellow eyes come from a native 64×16, 44-frame GIF. Source, checksum
and rights status are in [ART_SOURCES.md](ART_SOURCES.md). Downloaded and adapted
art is private; the code contains only its preparation logic.

## Method

The centre gap shows encoded fps above a three-digit frame counter. For longer
files the 44-frame eye motion repeats, while the index advances continuously.
Those counters make distinct decoded frames; repeating source poses does not
create more unique source animation poses. Prepared files are decoded offline to
check frame count, native size, encoded durations and loop metadata.

The source-backed GIF upload now supports multiple 12-KiB windows, bounded to
256 KiB per experiment and 600 decoded frames. Each window repeats whole-file
size and CRC32; the first has option 00, continuation windows 02, all in slot 0.
Every window waits for a five-byte `05 00 03 00 status` notification. Reference
window statuses 0/1/3 are accepted; the final window must return status 3.
No retries, parallel requests, persistent slots or per-frame streaming are used.
The entire upload has a 120-second timeout, plus existing write/reply timeouts.

The script disconnects after completion, then waits at least twelve seconds,
or two encoded loops plus two seconds, capped at sixty seconds. This gives time
for visual checks without any host frame writes. GIF frame delays are encoded
in whole centiseconds; tested target settings are 10/20/25/50 fps with
100/50/40/20 ms delays. Owner observations are not instrumented frame timing,
so an accepted 50 fps GIF alone cannot prove that the display renders 50 fps.

## Verified first step: 44 frames at encoded 10 fps

The 20,500-byte file uploaded in two windows, with statuses 1 then 3, in
4.237 seconds from first write to final reply. The owner confirmed correct,
steady eye motion and a counter repeating 001–044 after disconnect. The encoded
loop is 4.4 seconds. Capture: `captures/eyes-44f-10fps-20261114.jsonl` and its GIF.
This verifies the first multi-window upload and the larger real-art animation.

## Rate comparison: all four sections visually confirmed

One 176-frame file contains four consecutive 44-frame sections, labelled 10,
20, 25 and 50. Each section's counter restarts at 001. Encoded section lengths
are 4.4, 2.2, 1.76 and 0.88 seconds, totalling 9.24 seconds per loop. The file
is 81,791 bytes in seven windows. All windows were acknowledged, with statuses
1/1/1/1/1/1/3. Upload took 18.704 seconds from the first chunk attempt to the
final reply. The session disconnected, observed without writes and finished at
18:45:05.888 UTC. Capture: `captures/eyes-rate-comparison-20261114.jsonl`.
The transmitted windows were reconstructed and matched against the preview's
whole-file CRC, size and continuation headers. The owner confirmed:

> All four work and look progressively faster

Thus all four labelled sections render, including the 20 ms / encoded 50 fps
section, and the owner sees increasing speed. This is a qualitative playback
check; exact 50 fps rendering or the absence of individual dropped frames was
not instrumented. The highest encoded rate tested is 50 fps, not a proven
physical maximum or a Bluetooth streaming rate.

Prepared capacity variants at encoded 20 fps are 132, 264 and 528 frames.
The 132/264 variants were not uploaded; after the successful rate comparison,
the 528-frame variant was tested directly.

## Capacity result: 528 frames at encoded 20 fps

The 244,687-byte GIF contains 528 distinct numbered frames, using repeated
44-frame source motion. All frame delays are 50 ms; the encoded loop is
26.4 seconds. It uploaded in twenty windows, with nineteen status-1 replies
and a final `0500030003`. There were no errors or retries.

| Trial | Decoded GIF frames | Encoded delays | GIF bytes | Windows / GATT chunks | Upload to final reply |
| --- | --- | --- | --- | --- | --- |
| Initial eyes | 44 | 100 ms | 20,500 | 2 / 85 | 4.237 s |
| Four-rate comparison | 176 (44 per section) | 100 / 50 / 40 / 20 ms | 81,791 | 7 / 340 | 18.704 s |
| Long eyes loop | 528 | 50 ms | 244,687 | 20 / 1,016 | 54.824 s |

All upload timings exclude discovery, connection, information/version exchanges
and disconnected observation. Last advertisement RSSI was respectively -81,
-72 and -64 dBm, a scan snapshot rather than a live measurement.

The long-file upload ran 18:50:20.766–18:51:15.591 UTC. The PC then disconnected
and sent no application writes during 54.8 seconds of observation, finishing at
18:52:10.551 UTC. Asked whether the counter reached the 500s and 528 before
restarting at 001, without freezes/corruption/early reset, the owner confirmed:

> It reaches 528, loops back to 001 and looks correct

This establishes that the file plays through its high counter values and loops
locally. It does not instrument every displayed frame or prove uniform 20 fps.
All transmitted windows were reconstructed offline and matched the saved GIF,
including window lengths, continuation options, repeated full-file size and CRC.

**Observed lower bounds:** a 528-frame / 244,687-byte local GIF works, and the
separate rate comparison renders all four encoded settings through 50 fps with
owner-reported increasing speed. The 528-frame capacity test was at encoded
20 fps; 528 frames at 50 fps were not tested. Neither the panel's maximum GIF
size/frame count nor its exact maximum physical playback rate has been found.
The current 256-KiB and 600-frame bounds are conservative tool limits, not
hardware specifications. Tests beyond them need an explicit bounded extension.

Private evidence:

- `captures/eyes-44f-10fps-20261114.jsonl`, preview and observation sidecar.
- `captures/eyes-rate-comparison-20261114.jsonl`, preview and observation sidecar.
- `captures/eyes-528f-20fps-20261114.jsonl`, preview and observation sidecar.
- `captures/eyes-bench-20261114/manifest.json` and `transport-summary.json`.

At the end of this stage the 528-frame animation remained on the panel. This
stage tested no persistent slot or power cycle. Later actual-library tests
confirmed through 4,096 numbered frames (1,915,364 bytes, encoded 204.8 seconds)
and separately verified retention of a tiny original slot-1 GIF. See
[LIBRARY_PANEL_TESTS.md](LIBRARY_PANEL_TESTS.md) for the latest results.

## Reproduce

With an identified panel in `$deviceId` and the prepared private input file,
choose fresh output names:

```powershell
.\.venv\Scripts\python.exe examples\gif_animation.py $deviceId --windows-cached-services --input captures\eyes-bench-20261114\eyes-528f-20fps.gif --output captures\eyes-capacity-new.jsonl --preview captures\eyes-capacity-new.gif
```

Preparation helpers are `prepare_eyes_gif(source_bytes, frames=528, fps=20)` and
`prepare_rate_comparison(source_bytes)` in `art_animation.py`. The upload accepts
only native 64×16 GIFs within the experiment bounds. It validates frames/delays
before connecting and never retries partial windows.

Automated verification: 123 tests passed. These include continuation-window
framing, full-file size/CRC repeated in every window, exact variable GIF delays,
176-frame rate sections, and preparation of 528 distinct numbered frames.
None of the automated tests access hardware.
