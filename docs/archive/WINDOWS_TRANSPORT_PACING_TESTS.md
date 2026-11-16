# Fast writes and frame pacing with the Windows throughput preference

These are two separate experiments requested after the owner-confirmed
[Windows connection preference tests](WINDOWS_CONNECTION_TESTS.md). The earlier
tuned two-minute run reached 11.908 uploads/second at requested 12 fps, with
1,429 of 1,440 source states uploaded and correct rendering throughout.

## Common controls

The runner is `examples/windows_connection_stream.py`, using the unchanged
installed upstream checkout at `c8cbaebca6df7797a7bcface8a1c4ca33e499973`.
Upstream owns all PNG framing, CRCs, chunks, ACK handling and serialized writes.
The scoped Windows throughput request is held during each stream, then closed
before disconnecting. Connection parameters are recorded before and after.

Every frame is a complete native 64x16 RGB PNG in non-saving slot 0, fitting
one supported write. There is at most one image outstanding and exactly one
required `0500020003` completion reply per image. Latest-state selection skips
source states when behind schedule. The normal 20-Hz game simulation is
unchanged. The separate END marker always uses acknowledged writes, even in a
fast run. On error, the test closes the connection before a fresh conventional
STOP 0 PNG recovery attempt. Production defaults are unchanged.

The runner now measures each positive scheduled wait directly: requested
duration and actual excess delay after the await. Zero-duration yields are
counted separately. The summary includes the final duration wait if one occurs.
These measurements include scheduler delays; they do not isolate one operating
system component as their cause.

## Stage one: fast PNG writes plus throughput preference

Compare fresh acknowledged and fast runs, each requesting 450 images over
30 seconds at 15 fps. The concatenated source SHA256 is
`1dac1101534dae972bf9ac93ea40d141ae2ba6f2b0f4c1e747d4c7594e8d5560`;
framed PNGs are 157-255 bytes. Only the PNG write-response flag changes.
Normal timer behaviour remains selected in both runs.

Fast mode removes each GATT write-response wait, while retaining the image's
final completion wait. It does not overlap images or concatenate commands.
The helper checks payload size against both the negotiated chunk size and
the characteristic's write-without-response limit before writing.

The fresh acknowledged control completed 392/450 images in 30.014 seconds:
13.061 completion replies/second, with 58 source states skipped. Reply latency
was 74.975 ms median, 89.952 ms p95 and 104.933 ms maximum. Its END marker was
392, its final connection interval was 15 ms, and it released the preference
and disconnected cleanly. All scheduler waits were zero-duration yields at
this requested 15-fps rate, because image completion dominated the schedule.
The matching fast run completed 387/450 images in 30.029 seconds:
12.888 completion replies/second, with 63 states skipped. Its median reply
latency was 74.992 ms, p95 90.207 ms and maximum 105.292 ms. It ended at END 387,
reported a final 15-ms connection interval, released the preference and
disconnected cleanly. Fast mode did not improve throughput in this pair; the
roughly 1.3% lower rate is not evidence of a reliable disadvantage either.
The owner confirmed they watched the fast run and it stayed correct throughout.
This confirms the tested small-PNG workload under this combination; earlier
fast GIF and native-pixel failures remain unresolved.

| Metric | Acknowledged | Fast |
| --- | ---: | ---: |
| Completed uploads | 392 | 387 |
| Skipped source states | 58 | 63 |
| Completion replies/second | 13.061 | 12.888 |
| Median completion time | 74.975 ms | 74.992 ms |
| p95 completion time | 89.952 ms | 90.207 ms |

Private captures:

- `captures/windows-round2-ack-throughput-15fps-30s-20261116.jsonl`
- `captures/windows-round2-fast-throughput-15fps-30s-20261116.jsonl`

## Stage two: scoped timer precision

First measure ordinary asyncio waits without the panel, comparing default
timing, a scoped 1-ms request, and default timing again. Then compare matched
two-minute 12-fps game runs with acknowledged writes and the same throughput
preference. Fast mode is disabled in this stage to isolate timing behaviour.
The 1,440 PNG source hash is
`bd4fcc8c61a0e746544324264f41b5d2b010bfc2fe13d7de8e8c5ea88698e7aa`.

The temporary request uses
[timeBeginPeriod](https://learn.microsoft.com/en-us/windows/win32/api/timeapi/nf-timeapi-timebeginperiod)
and matches it with
[timeEndPeriod](https://learn.microsoft.com/en-us/windows/win32/api/timeapi/nf-timeapi-timeendperiod)
in a `finally` block, with the same 1-ms period. Microsoft documents the modern
request as process-scoped and does not guarantee that every wait achieves that
resolution. This is why actual waits and upload scheduling are measured.
No registry setting, driver change, busy spin or custom sleep implementation
is introduced. The stream still uses its ordinary `asyncio.sleep` schedule.

The timer-only probe awaited 8 ms one hundred times per phase in one process:

| Phase | Median excess wait | p95 excess wait | Total duration |
| --- | ---: | ---: | ---: |
| Default before | 7.310 ms | 8.390 ms | 1.551 s |
| 1-ms request | 0.364 ms | 1.505 ms | 0.864 s |
| Default after release | 7.312 ms | 7.732 ms | 1.544 s |

The request was accepted and released successfully. The return to ordinary
wait times after release supports the scoped nature of this intervention.
The probe had no panel connection and does not establish improved upload
throughput. Private capture: `captures/windows-timer-sleep-probe-20261116.jsonl`.

The fresh normal-timing panel control completed all 1,440 uploads in 120.013
seconds: 11.999 uploads/second, with no skipped source states. Every completed
image and END 1440 received its strict reply. Median image completion time was
74.856 ms, p95 90.031 ms and maximum 126.661 ms. The 764 positive scheduled
waits had median excess delay 9.989 ms, p95 15.049 ms and maximum 16.274 ms.
The final connection interval was 15 ms; the preference was released and the
session disconnected cleanly. Private capture:
`captures/windows-round2-timing-control-12fps-120s-20261116.jsonl`.

This control had no misses despite the earlier comparable run's eleven misses.
Do not attribute a later complete run solely to the timer request. The matched
comparison also examines directly measured waits, deadline lateness and
inter-update intervals.

The 1-ms run completed 1,439 of 1,440 uploads in 120.002 seconds: 11.992
completion replies/second, with one skipped source state. Every completed
upload and END 1439 received exactly its expected final reply. The timer
request was released successfully (return status zero), the Windows preference
was released, and the connection closed cleanly. The final interval was 15 ms.
Private capture: `captures/windows-round2-timing-1ms-12fps-120s-20261116.jsonl`.
The owner confirmed: "Watched the full run; correct throughout."

| Metric | Normal timing | Scoped 1-ms request |
| --- | ---: | ---: |
| Completed source uploads | 1,440 | 1,439 |
| Skipped source states | 0 | 1 |
| Completion replies/second | 11.999 | 11.992 |
| Image completion time, median | 74.856 ms | 73.602 ms |
| Image completion time, p95 | 90.031 ms | 90.055 ms |
| Positive scheduled waits | 764 | 1,143 |
| Scheduled wait excess, median | 9.989 ms | 0.748 ms |
| Scheduled wait excess, p95 | 15.049 ms | 1.446 ms |
| Source deadline lateness, median | 8.415 ms | 0.973 ms |
| Source deadline lateness, p95 | 20.457 ms | 16.410 ms |
| Source deadline lateness, maximum | 58.883 ms | 77.962 ms |
| Source interval absolute error, median | 8.162 ms | 0.567 ms |
| Source interval absolute error, p95 | 12.823 ms | 8.435 ms |
| Source interval absolute error, maximum | 43.429 ms | 61.526 ms |

Source deadline lateness is actual upload start minus `(source_frame - 1) / fps`,
clamped to zero. Source interval absolute error compares successive start
intervals with the source-frame index difference divided by fps, including the
one skipped-state interval. These are host submission timings, not measured
physical refresh or input-to-display latency.

Typical scheduled waits and starts were substantially closer to their deadlines
with the request. Image completion latency stayed roughly the same. Both streams
were capped at 12 fps, so this pair does not establish a higher maximum upload
rate. It also does not establish fewer schedule misses: the normal control
already had none, and the timer run had one. The worst deadline and interval
outliers were larger in the timer run despite its better median and p95. Do not
claim uniformly better timing, visibly smoother presentation, or a stable
15-fps result from these data.

The practical outcome is to retain acknowledged writes. The scoped 1-ms request
is a potential pacing option, while the throughput preference remains the
measured speed improvement. No production defaults were changed. No hardware
test remains running; the panel's last acknowledged image was END 1439. Both
the fast experiment and the 1-ms timing experiment have owner-confirmed correct
playback. The new normal-timing control has protocol verification; no separate
full-run owner observation was requested for it. No subjective smoothness
improvement was established.

A timer request being accepted does not establish better frame pacing.
Completion replies measure upload throughput, not physical LED refresh.
Visual observations are recorded separately.

## Verification

All 209 tests pass under the unchanged library, with four optional grouped-pixel
builder tests skipped. Seventeen focused Windows tests cover connection
request scope, actual versus requested intervals, timer release on failure,
timer request rejection and release errors, default timing making no request,
scheduled-wait instrumentation, unchanged upstream image ACK policies, and
fast-write limits checked before a write.

Use fresh output paths when repeating a run:

```powershell
.\.venv\Scripts\python.exe examples\windows_connection_stream.py $deviceId --profile throughput --fps 15 --seconds 30 --output captures\tuned-ack-new.jsonl
.\.venv\Scripts\python.exe examples\windows_connection_stream.py $deviceId --profile throughput --fps 15 --seconds 30 --fast --output captures\tuned-fast-new.jsonl
.\.venv\Scripts\python.exe examples\windows_connection_stream.py $deviceId --profile throughput --fps 12 --seconds 120 --output captures\timing-control-new.jsonl
.\.venv\Scripts\python.exe examples\windows_connection_stream.py $deviceId --profile throughput --fps 12 --seconds 120 --timer-ms 1 --output captures\timing-1ms-new.jsonl
```

No results from this round have been posted upstream.
