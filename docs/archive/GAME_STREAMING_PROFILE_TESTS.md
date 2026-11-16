# Optional Windows game streaming profile

## Implemented behaviour

All games share a Panel updates selector: Standard (10 fps) is the default;
Windows (12 fps) is offered on Windows. The requested choice is saved alongside
the existing panel target and applied on the next connection. Existing settings
without this field select Standard. The selector is locked while connecting or
connected, and enabled again on disconnect.

The optional profile acquires a scoped Windows throughput preference after the
normal panel check. It uses 12-fps output only after request acceptance and a
reported 15-ms interval with zero peripheral latency. Missing APIs, refused
requests and unmatched negotiation fall back to Standard, with a visible status
and detailed local logs. A reconnect retries the requested profile with a fresh
request. The request closes on normal exit, error or cancellation.

The existing experimental request implementation was moved into
`src/led_matrix_hacker/windows_connection.py` so the experiment and app use the
same code. This still accesses Bleak's private WinRT requester. The Windows
option remains optional because availability and negotiation depend on the
host, backend and device. An initial interval snapshot does not guarantee the
interval for the whole session.

Both profiles retain acknowledged GATT writes, MTU-limited chunks up to 500
bytes, strict final PNG replies, non-saving slot 0, one pending image and the
latest-state mailbox. Windows mode uses fixed deadlines and skips elapsed
slots. Standard keeps its existing minimum interval between upload starts.
Neither profile changes game simulation speed. Fast writes and timer precision
remain in the experiments.

## Automated and desktop checks, 2026-11-16

Full suite: **231 passed, 4 skipped**. The skips require the optional isolated
upstream grouped-pixel PR. Run with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

The new integration tests exercise negotiation versus acceptance, unavailable
backends/platforms, refused requests, releasing an unused request before
fallback, propagation of upload errors/cancellation, fresh requests on
reconnect, cancellation of an outstanding upload, saved preferences and legacy
settings. Deterministic pacing checks cover both rates, sleep overshoot and a
transport slower than the requested rate.

A hidden-window desktop check instantiated Snake, Starfall and Micromaze. It
verified that each loads the saved Windows choice, passes it to the worker,
locks the selector during a connection, displays a Standard fallback and unlocks
the selector on disconnect. That check used a fake worker, with no BLE access.

## Real-worker panel checks

These checks used the production PanelWorker and mailbox with a live 20-Hz
Starfall simulation, normal rules and scripted controls. Frames were generated
as the game ran, rather than replayed from pre-rendered PNGs. Each trial ran for
about 12 seconds after connecting, then closed the worker and disconnected.
The second trial used a fresh worker and connection. These short trials were
followed by the manual keyboard check described below.

The first pair enabled the preference but retained the old relative pacing.
They completed 129 and 130 acknowledged images, with measured completion rates
of 10.816 and 10.859 uploads/s. Relative sleeps accumulated scheduler overshoot,
which motivated fixed deadlines for the optional mode.

After that correction:

| Metric | First connection | Fresh reconnect |
| --- | ---: | ---: |
| Completed PNG uploads / strict final replies | 143 / 143 | 144 / 144 |
| Completion rate between first and last replies | 11.983/s | 11.992/s |
| Median image reply time | 74.493 ms | 74.513 ms |
| Largest interval between completions | 120.056 ms | 120.139 ms |
| Preference requested / released | 1 / 1 | 1 / 1 |
| Session errors | 0 | 0 |

All recorded game frames were in the running phase. Both sessions ended
cleanly; cancellation can interrupt an additional pending upload during
shutdown, which is not counted as a completed image. No ambiguous pending upload
was retried on the same connection. The next trial started a fresh connection.

The final tests left the last game image on the panel after disconnecting; no
END marker was uploaded. The owner reported "screen froze" after these checks.
The owner could not identify when it stopped, and described a ship firing with
a power-up visible. Extracting the last acknowledged PNG from the capture
showed a cyan ship on the left, yellow shots across the screen, a cyan T near
the middle and a green enemy low on the right. This matches that description
and is consistent with the intended held final frame. The following attempted
image differs slightly but shows the same scene. This does not establish whether
there was an earlier freeze, or confirm correct playback throughout the runs.
Protocol results do not establish visual success for those short trials.

A subsequent fresh conventional connection uploaded END 144 and received its
strict final reply, then disconnected. This marker was sent separately after
the timing confusion; it was not part of the original performance measurements.
The real Starfall UI was then opened with the Windows profile selected and an
isolated play-test capture directory. It waited for Enter to start. The owner
played, disconnected, reconnected and resumed, then confirmed: "Both worked,
but reconnect took a few seconds longer than I'd have expected. That might be
normal though." This confirms correct rendering and reconnect for that manual
session, without establishing measured input-to-display latency or broader
device compatibility.

The first interactive connection completed 732 strict-acknowledged game images
and released its preference on disconnect. One intervening connection attempt
was cancelled during scanning after 8.500 seconds, before a preference was
acquired. The subsequent connection again enabled Windows 12 fps, completed 76
images before pausing, and had no recorded upload or connection error at the
time of the owner's response. The UI remained open and paused.

### Why reconnect took time

The successful reconnect spent 15.036 seconds resolving the device, then 0.854
seconds establishing the connection/notifications and another 0.149 seconds on
the panel query. The optional preference was ready immediately after that query;
the complete preparation time was about 16.040 seconds. The first interactive
connection similarly spent 15.203 seconds scanning and became ready after
16.484 seconds from scan start.

This delay was explained by the previous `resolve_device` implementation: it
calls `BleakScanner.discover` for the complete 15-second scan before selecting
the saved identifier. It is not a measured delay introduced by the 12-fps
preference. The subsequent discovery improvement below removes that fixed wait
for saved platform identifiers.

## Early discovery improvement

`resolve_device` now uses Bleak's existing `find_device_by_address` for Bluetooth
MAC addresses and macOS UUID identifiers. It returns on the matching
advertisement, with the same bounded timeout if the panel is not found. It does
not perform a second scan or treat a missing address as another device's name.
Other identifiers/names retain the full discovery scan and duplicate-name check.
The general scan command still scans for its full requested duration.

Final suite after this change: **242 passed, 4 optional tests skipped**. Added
cases cover address/UUID lookup, case-insensitive addresses, a competing device
named after the target address, missing addresses without a second scan,
duplicate names, cancellation before connection, and invalid timeouts.

The paused Starfall test window was closed normally before hardware checks;
its worker released the held preference and disconnected. Two fresh production
PanelWorker sessions selected Windows 12 fps, sent one acknowledged END marker
each, released the preference and disconnected. These static checks did not
start gameplay and do not add visual streaming evidence.

| Stage | First connection | Fresh reconnect |
| --- | ---: | ---: |
| Discovery | 0.706 s | 2.036 s |
| Connection/notifications | 0.689 s | 0.710 s |
| Panel query and Windows profile | 0.166 s | 0.167 s |
| Total ready time from scan start | **1.561 s** | **2.912 s** |
| Acknowledged final marker | END 1 | END 2 |

This removes the fixed 15-second scan delay for the tested saved address. It
does not guarantee every connection will complete within three seconds:
advertising, radio conditions and platform connection timing still vary.
The test UI was subsequently reopened with the updated code and Windows
profile selected. It became ready in 1.562 seconds from scan start, received
the ready image's strict reply and waited for Enter. No connection or UI error
was recorded at that point. Private log:
`captures/windows-profile-playtest-20261116-203710/starfall-20261116-215156-160206.jsonl`.
The owner subsequently accepted the result: "Allright - that's a success."
This confirms acceptance of the reconnect improvement after reopening the app;
it does not add a separately timed continuous-playback test.

Private captures:

- `captures/game-profile-worker-20261116-203457-{1,2}.jsonl`: relative pacing.
- `captures/game-profile-worker-20261116-203710-{1,2}.jsonl`: fixed deadlines.
- `captures/game-profile-worker-20261116-203710-summary.json`: final pair summary.
- `captures/windows-profile-playtest-20261116-203710/starfall-*.jsonl`: manual
  game, cancelled scan and successful reconnect.
- `captures/windows-profile-playtest-20261116-203710/owner-observation.json`:
  owner confirmation and reconnect timing analysis.
- `captures/early-reconnect-20261116-205037-{1,2}.jsonl`: early-discovery
  production worker sessions and acknowledged END markers.
- `captures/early-reconnect-20261116-205037-summary.json`: timing summaries.

No upstream source was changed and no results were posted upstream.
