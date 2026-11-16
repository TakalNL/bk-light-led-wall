# Windows BLE connection preference experiment

This checks whether Windows connection scheduling contributes to the observed
roughly 45-ms acknowledged writes and 90-ms final PNG completion replies. It
uses the verified sequential PNG path without pipelining, command concatenation
or writes without response. The production app and installed upstream library
are unchanged.

## API and scope

Windows 11 provides
[RequestPreferredConnectionParameters](https://learn.microsoft.com/en-us/uwp/api/windows.devices.bluetooth.bluetoothledevice.requestpreferredconnectionparameters)
and a
[ThroughputOptimized preference](https://learn.microsoft.com/en-us/uwp/api/windows.devices.bluetooth.bluetoothlepreferredconnectionparameters).
The local Windows build is 26300, and the installed WinRT projection exposes
the request and actual-parameter APIs. Its throughput preference asks for
interval units 12 through 12 (15 ms), peripheral latency zero, and a 2-second
supervision timeout. The interval is a request, not an established measurement
of this panel.

Microsoft specifies that
[request status Success](https://learn.microsoft.com/en-us/uwp/api/windows.devices.bluetooth.bluetoothlepreferredconnectionparametersrequeststatus)
means the system accepted a request; actual parameters are negotiated separately.
The experiment records
[GetConnectionParameters](https://learn.microsoft.com/en-us/uwp/api/windows.devices.bluetooth.bluetoothleconnectionparameters)
before the request, after up to five seconds of negotiation, and after streaming.
Interval units are 1.25 ms; peripheral latency is measured in connection events.

`examples/windows_connection_stream.py` holds the preference request only
inside the test connection, closes it on normal completion or failure, and
disconnects. It changes no registry, driver, global power setting or saved
panel content. The Windows throughput preference can reduce the number of
simultaneous Bluetooth connections the radio supports, so it is not enabled
globally. The normal profile makes no preference request.

The only backend-specific access is the connected Bleak WinRT requester's
private `_backend._requester` object. The experimental helper checks that it
exists and exposes the required methods. All packet construction, ACK handling,
serialized writes and connection cleanup use the existing upstream-backed app
adapter. Each complete PNG must receive exactly `0500020003`.

## Comparison

Both runs request 15 fps for 30 seconds using the same 450 Starfall source PNGs
as the prior pipeline control. The ordinary game simulation stays at 20 Hz with
normal rules. The concatenated input SHA256 is
`1dac1101534dae972bf9ac93ea40d141ae2ba6f2b0f4c1e747d4c7594e8d5560`.
Each framed image is 157-255 bytes and fits in one acknowledged 500-byte write.
There is at most one outstanding image. A standard END marker follows each
stream. Images use non-saving slot 0.

API acceptance alone must not be reported as a successful interval change or
FPS improvement. Throughput counts completion replies, not directly measured
physical display refresh.

### Default profile, 2026-11-16

The fresh default connection initially reported interval 15 ms, peripheral
latency zero, and supervision timeout 9.6 seconds. At the end of the stream it
reported interval **22.5 ms**, latency zero, and supervision timeout 6 seconds.
The initial parameters therefore did not describe the entire run. The exact
transition time was not sampled.

It completed 326 of 450 images in 30.059 seconds: **10.845 completion
replies/second**, skipping 124 scheduled source states. Reply latency was
89.964 ms median, 112.579 ms p95 and 134.960 ms maximum. Each upload and END 326
received exactly the expected final reply. The connection closed cleanly.
Private capture: `captures/windows-default-15fps-30s-20261116.jsonl`.

### Throughput profile

Windows accepted the request (status Success). The connection reported interval
15 ms and peripheral latency zero before streaming and again afterwards; the
final supervision timeout was 2 seconds. The request was explicitly closed,
and the connection disconnected cleanly. Before/after snapshots do not prove
a constant interval at every point during either stream.

| Metric | Default | Throughput preference |
| --- | ---: | ---: |
| Requested source updates | 450 | 450 |
| Completed with exact final replies | 326 | 389 |
| Skipped source states | 124 | 61 |
| Stream duration | 30.059 s | 30.014 s |
| Completion replies/second | 10.845 | 12.961 |
| Reply time, median | 89.964 ms | 75.006 ms |
| Reply time, p95 | 112.579 ms | 90.252 ms |
| Reply time, maximum | 134.960 ms | 121.394 ms |
| Interval before stream | 15 ms | 15 ms |
| Interval after stream | 22.5 ms | 15 ms |
| Final marker | END 326 | END 389 |

The measured upload rate was about 19.5% higher with the throughput preference
in this sequential pair. The owner confirmed correct rendering in that run but
could not judge smoothness. Do not claim a visible smoothness improvement or a
sustained 15-fps result. The profile's result is consistent with shorter
connection scheduling improving throughput, but one pair on one Windows
host/panel does not establish causation or broader platform support.

Each of the 389 images and the separate END marker received exactly its strict
completion reply. Private capture:
`captures/windows-throughput-15fps-30s-20261116.jsonl`.

### Two-minute 12-fps validation

A follow-up requested 1,440 PNG uploads at 12 fps over 120 seconds with the
same scoped throughput preference. The game still simulates at its normal
20 Hz; only output sampling changes. This target is below the first tuned
run's measured average. All framed images are 157-322 bytes. The source SHA256
is `bd4fcc8c61a0e746544324264f41b5d2b010bfc2fe13d7de8e8c5ea88698e7aa`,
and its final game state matches the original two-minute 10-fps pilot. Private
capture: `captures/windows-throughput-12fps-120s-20261116.jsonl`.
It completed **1,429 of 1,440 scheduled uploads** in 120.007 seconds:
**11.908 completion replies/second**. Eleven source states were skipped by the
latest-state scheduler (0.76% of requested states); this is not a measurement of
lost or dropped physical LED frames. Reply time was 74.981 ms median, 104.626 ms
p95 and 135.035 ms maximum. The source pilot still reached its normal final
state, and the final marker was END 1429.

All 1,429 completed uploads and the separate END marker received exactly one
strict final reply. The post-stream connection snapshot reported interval
15 ms, peripheral latency zero and supervision timeout 2 seconds. The request
was released and the connection closed cleanly, with no reconnect during the
stream or protocol error. The owner confirmed: "Watched the full run; correct
throughout."

This establishes a measured upload rate close to 12 fps for this workload over
two minutes, with a small number of schedule misses. It is not a complete
1,440-frame pass, a claim of exact physical refresh, or proof of visibly smoother
motion. Both the initial 30-second tuned run and the fully watched two-minute
run now have independent owner confirmation of correct rendering. The owner
could not judge smoothness in the initial comparison, so no visible smoothness
improvement is claimed. The production transport and its 10-fps default remain
unchanged. No hardware test is running.

## Verification and reproduction

Eight focused tests cover unit conversion, inactive connections, accepted and
rejected requests, accepted requests with unchanged actual parameters, cleanup
after a stream failure, and the default profile making no request.
The initial validation passed 200 tests, with four optional grouped-builder
tests skipped under the unchanged dependency. The later
[fast-write and pacing experiments](WINDOWS_TRANSPORT_PACING_TESTS.md) expand
the full suite to 209 passing tests and the Windows-focused suite to seventeen.

Use fresh capture filenames:

```powershell
.\.venv\Scripts\python.exe examples\windows_connection_stream.py $deviceId --profile default --fps 15 --seconds 30 --output captures\windows-default-new.jsonl
.\.venv\Scripts\python.exe examples\windows_connection_stream.py $deviceId --profile throughput --fps 15 --seconds 30 --output captures\windows-throughput-new.jsonl
.\.venv\Scripts\python.exe examples\windows_connection_stream.py $deviceId --profile throughput --fps 12 --seconds 120 --output captures\windows-throughput12-new.jsonl
```

Private captures include device information and full packet traces. No results
from this experiment have been posted upstream.
