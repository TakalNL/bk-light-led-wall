# Host-streamed sprite animation

A later [panel-local GIF experiment](GIF_TESTS.md) verified looping after the PC
disconnects, with owner-reported steady-looking timing. The runs below measure
the separate host-streaming approach and preserve its observed timing variation.

Date: 2026-11-14. Verified 64×16 B.K. Light panel at the reported approximately
two-metre desk location, separate USB supply and installed PC antennas. The
previous three antenna PNG trials succeeded at this placement.

## First bounded run

`examples/sprite_animation.py` prepared twenty distinct RGB PNGs before connecting.
A yellow 8×8 sprite moves left to right inside a blue border, with a green
progress line. The final frame adds END and leaves the sprite at the right.
The host uploaded each frame using the verified PNG/CRC format and slot 0.
This is host streaming; no stored animation or GIF command was sent.

One cached-FA-service connection performs the information/Berlin clock and
version exchanges, then starts frames on absolute half-second deadlines. Each
frame waits for its PNG reply before another can start. There is no retry,
background queue or catch-up burst. Unexpected image replies, request failures,
or schedule lateness above 250 ms stop playback; playback also has a 15-second
outer timeout. The planned twenty-frame pass includes a final half-second hold.

| Measurement | Result |
| --- | --- |
| Playback start/end | 18:17:22.518–18:17:32.524 UTC / 19:17:22.518–19:17:32.524 CET |
| Frames / target rate | 20 / 2 fps |
| Playback duration | 10.005563 seconds, excluding scan and connection/setup |
| Image replies | 20/20 exactly `0500020003` |
| Request-to-reply latency, min / median / max | 47.956 / 54.875 / 140.629 ms |
| Frame-start intervals, min / max | 493.865 / 513.139 ms |
| Maximum start lateness | 15.959 ms |
| Total application frame bytes / GATT chunks | 3708 / 21 |
| Last scan advertisement RSSI | -67 dBm, snapshot rather than live RSSI |
| Failures / retries | 0 / 0 |

After the final frame, hold and clean disconnect, the owner confirmed:

> Yes, regular movement and END; no glitches

This validates the visible ten-second 2 fps sprite pass in the current setup.
It does not establish a maximum frame rate, longer-duration stability or timing
for more complex images. The simple frames compressed to one GATT chunk each,
except the final END frame which required two. Higher rates or image sizes need
their own measurements. Offline verification reconstructed every transmitted
frame and matched it to its saved preview, including the PNG/CRC header.

Private evidence:

- `captures/sprite-2fps-20261114.jsonl`
- `captures/sprite-2fps-20261114/01.png` through `20.png`
- `captures/sprite-2fps-20261114-observation.md`

## Reproduce the same bounded test

With the previously identified device in `$deviceId`, use new capture paths:

```powershell
.\.venv\Scripts\python.exe examples\sprite_animation.py $deviceId --windows-cached-services --output captures\sprite-new.jsonl --previews captures\sprite-new
```

The preview directory must not exist. The default remains 20 frames at 2 fps
over ten seconds. Visual questions follow the `finished` event.

## Five fps with a visible counter

The owner requested a visible counter to help spot missing frames, then authorized
the proposed 5 fps test. The new `--fps 5 --frame-counter` options prepare fifty
PNG frames. A white 3×5 pixel counter, `01/50` through `50/50`, sits below the
sprite without overlapping it; the final frame also shows END. The sprite uses
rows 1–8, a green progress line uses row 9, and the counter uses rows 10–14.
The same reported desk placement, separate supply and PC antennas were retained.

Playback uses absolute 200 ms deadlines and one outstanding frame. The lateness
limit is half a frame period: 100 ms at 5 fps, retaining 250 ms for the 2 fps run.
The two-second image-reply timeout, 15-second outer playback limit, stop-on-error
behavior and lack of retries remain unchanged. There is no frame skipping or
background queue in the sender.

| Measurement | Result |
| --- | --- |
| Playback start/end | 18:21:41.000–18:21:51.004 UTC / 19:21:41.000–19:21:51.004 CET |
| Frames / target rate | 50 / 5 fps |
| Playback duration | 10.004107 seconds, excluding scan and connection/setup |
| Image replies | 50/50 exactly `0500020003`, in frame order |
| Request-to-reply latency, min / median / max | 48.157 / 61.442 / 99.072 ms |
| Frame-start intervals, min / max | 185.353 / 210.670 ms |
| Maximum start lateness | 15.913 ms |
| Application frame sizes | 224–255 bytes |
| Total application frame bytes / GATT chunks | 11684 / 51 |
| Last scan advertisement RSSI | -78 dBm, snapshot rather than live RSSI |
| Failures / retries | 0 / 0 |

After playback finished and disconnected, the owner confirmed:

> Counter progressed normally; 50/50 and END, no glitches

All fifty transmitted frames were reconstructed offline and matched against
their saved PNG previews and CRC framing. This verifies a visible ten-second
5 fps pass with no skips reported by the owner. It is not an instrumented
per-frame display capture or a test of longer-duration stability or maximum
frame rate. The counter also changes image complexity compared with the original
2 fps test, so this is not a rate-only comparison. All but the final image fit
one GATT chunk; the final image required two.

Private evidence:

- `captures/sprite-5fps-counter-20261114.jsonl`
- `captures/sprite-5fps-counter-20261114/01.png` through `50.png`
- `captures/sprite-5fps-counter-20261114-observation.md`

To repeat this condition with new output paths:

```powershell
.\.venv\Scripts\python.exe examples\sprite_animation.py $deviceId --windows-cached-services --fps 5 --frame-counter --output captures\sprite-5fps-new.jsonl --previews captures\sprite-5fps-new
```

Automated verification: 98 tests passed, including the original 2 fps behavior,
5 fps scheduling and stop threshold, and decoding all fifty rendered counters
to verify their frame numbers and separation from the sprite. Tests use no hardware.

## One minute at five fps

The owner authorized a one-minute check with the visible counter. The example
now accepts `--duration 60`, preparing 300 PNGs before connection. The counter
uses three digits, `001/300` through `300/300`; END sits beside it on the final
image. The sprite repeats its ten-second crossing six times while the counter
advances continuously. The reported desk placement, separate supply and PC
antennas remain the same. This is one continuous BLE connection and playback.

The 200 ms absolute schedule, 100 ms lateness guard, one-frame-at-a-time requests,
and no-retry policy are unchanged. The outer playback timeout scales to duration
plus five seconds (65 seconds here); scan/setup occur before this timeout.
The notification capture cap increased from 256 to 512 so all 302 expected
notifications (information, versions and 300 images) could be retained.

| Measurement | Result |
| --- | --- |
| Playback start/end | 18:25:59.783–18:26:59.785 UTC / 19:25:59.783–19:26:59.785 CET |
| Frames / target rate | 300 / 5 fps |
| Playback duration | 60.002591 seconds, excluding scan and connection/setup |
| Image replies | 300/300 exactly `0500020003`, in frame order |
| Request-to-reply latency, min / median / max | 47.820 / 64.634 / 176.862 ms |
| Frame-start intervals, min / max | 184.990 / 215.322 ms |
| Maximum start lateness | 16.218 ms |
| Image-reply intervals, min / max | 109.768 / 295.166 ms |
| Application frame sizes | 229–256 bytes |
| Total application frame bytes / GATT chunks | 72587 / 380 |
| One-chunk / two-chunk images | 220 / 80 |
| Last scan advertisement RSSI | -73 dBm, snapshot rather than live RSSI |
| Failures / retries | 0 / 0 |

After playback finished and disconnected, the owner reported seeing all 300
frames, but possibly unequal time between some frames; this was hard to judge.
Record this as **all frames visible, possible uneven pacing**, rather than a
confirmation of perfectly smooth motion. Upload starts stayed close to their
200 ms schedule, while request/reply latencies and reply intervals varied.
That is consistent with possible visible timing variation, but no instrumented
per-frame display timing was captured, and ACK arrival is not a measurement of
the exact instant a frame appears on the display.

The minute check verifies uninterrupted, acknowledged PNG streaming with every
frame reported visible in this setup. It does not establish uniform display
timing, indefinite stability or maximum frame rate. Fifty-nine frame requests
took over 100 ms, so a strict 10 fps schedule is not established by this run.
The wider counter also changes image sizes compared with the ten-second check.

Every frame was reconstructed offline and matched its preview and PNG/CRC header.
Private evidence:

- `captures/sprite-5fps-minute-20261114.jsonl`
- `captures/sprite-5fps-minute-20261114/01.png` through `300.png`
- `captures/sprite-5fps-minute-20261114-observation.md`
- `captures/sprite-5fps-minute-20261114-console.txt`

To repeat with new output paths:

```powershell
.\.venv\Scripts\python.exe examples\sprite_animation.py $deviceId --windows-cached-services --fps 5 --duration 60 --frame-counter --output captures\sprite-minute-new.jsonl --previews captures\sprite-minute-new
```

The supported durations are bounded to 10 or 60 seconds; the default remains
10 seconds. Automated verification: 107 tests passed, including minute scheduling,
three-digit counter transitions, sprite loops, separate END layout, duration
validation and bounded notification capture beyond 300 replies. Tests use no hardware.

## Later compact RGB library path

Using actual pinned `pypixelcolor` builders/transport with our Windows adapter,
a 3-by-5 bitmap HUD reduced complete RGB PNG messages to 246–267 bytes. With
500-byte acknowledged writes, 100/100 numbered frames at scheduled 10 fps
completed in 10.011 seconds and looked correct to the owner. The 15/20 fps
probes stopped at the script's timing cutoffs; fast native-pixel motion visibly
corrupted. These are separate scene/transport experiments, not a rate-only
comparison with the original sprite. Longer 10 fps stability and physical screen
timing remain unmeasured. See [LIBRARY_PANEL_TESTS.md](LIBRARY_PANEL_TESTS.md).
