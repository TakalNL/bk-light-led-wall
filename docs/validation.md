# Validation and evidence

Hardware observations below are from the owner's Windows host and 64x16 panels.
Protocol checks and owner visual observations are recorded separately.

Latest verified source checkpoint: **350 passed, four optional PR #88 cases
skipped**, after adding the web controller and individual-panel controls. This
is synthetic test coverage, not additional hardware/platform validation. See
[findings](investigation-summary.md) for the consolidated conclusions and
[compatibility](compatibility.md) for current support limits.

The sections below retain measurements and test counts from their respective
dates. Later follow-ups supersede earlier unresolved findings.

## Earlier application baseline, 16-19 November 2026

| Check | Result |
| --- | --- |
| Game output, Standard | Established acknowledged 10-fps path |
| Windows profile, two live-worker trials | 11.983 and 11.992 completed uploads/s |
| Interactive Windows-profile Starfall | Owner confirmed correct gameplay and reconnect |
| Saved-address reconnect, two worker checks | Ready in 1.561 and 2.912 s; previously about 16 s |
| Reopened real UI after discovery change | Ready in 1.562 s; owner accepted the result |
| Public-client chunk-size comparison | 1,175/1,200 default versus 1,200/1,200 with 500-byte chunks |
| Two-panel stacked wall, 2026-11-19 | Both type 0x83 / 64×16; 96 combined frames acknowledged |
| Wall completion time, same run | Mean 71.5 ms; maximum 118.767 ms; last 66.9 ms |
| Physical order | Owner confirmed cyan panel 1 above orange panel 2 |

At that checkpoint the source suite passed **288 tests**, with four optional upstream-branch
cases skipped. This includes settings and recording checks. Hidden desktop
checks confirmed all three games load the shared settings directly. Earlier
cleanup checks also covered profile selection, start/pause and disconnect.
At that cleanup checkpoint, a 46,072-byte wheel passed UI,
rendering and PNG-encoding checks from an independent environment outside the
source directory; developer tools were absent from that installation. This is
a packaging smoke check, not the still-outstanding clean-machine test.
Run the current suite using the command in [development](development.md).

The two-panel diagnostic used a shared 64×32 canvas and a 10-fps Standard target.
Its private capture is `captures/wall-20261119-130810-956161.jsonl`, with a matching
identify PNG. Both links were held simultaneously and each canvas version waited
for both image completion replies. Owner confirmation establishes physical order;
moving-image seam quality and physical refresh synchronization remain unmeasured.
Hidden Tk checks covered the wall's layout presets, reversal, rotation, demo,
full-canvas Snake, image fitting and media relayout. Synthetic checks cover exact
pixel crops, all mounting rotations, GIF timing/transparency, slow-panel frame
coordination, invalid replies, idle disconnection, setup failures, duplicate
physical devices and cancellation cleanup.

A follow-up run on the final device-metadata path completed another 30 shared
frames (`captures/wall-20261119-131648-022411.jsonl`). The visible desktop
controller then connected both panels in 6.95 seconds and completed 197 combined
frames without errors at the inspection checkpoint. It was left streaming the
seam demo. This verifies the UI-to-worker path as well as the diagnostic runner.

Variable compensation checks cover 0, 2, 3 and 32 pixels in both axes, exact
omission of hidden image rows/columns, black preview gaps, rotation/origin
preservation, settings round trips and invalid values. A slow-panel test changes
the image and gap while an upload is pending, verifying that the next frame
uses its matching layout. Live changes cannot replace connected device
identities. Hidden Tk checks exercised the gap controls while marked connected,
including preserving demo playback and saving/reloading the positions.

The live compensation check (`captures/wall-compensation-20261119-133011-114374.jsonl`)
kept both links open while switching from 0 to 2 to 3 pixels: 28, 26 and 28
combined frames were acknowledged respectively. The updated controller was then
reopened at 3 pixels (64×35 virtual canvas); its first inspection found 130
completed shared frames and no errors. The ring was left running for owner
assessment of the compensated seam.

The game-focused capability follow-up verified a fully native grouped-pixel
baseline, but mode-3 PNG preservation, horizontal mirroring and rightward
movement were not demonstrated in the owner-observed sequences. A two-panel
244/500/500/244-byte acknowledged-chunk comparison completed all 228 combined
frames (456 PNG uploads), at 4.623-5.180 completed canvases/s under those connection
conditions. Fewer GATT writes did not establish a consistent speed improvement.
See the [capability map](panel-capabilities.md#two-panel-acknowledged-chunk-comparison)
for conditions and the distinction between host completion and physical timing.

## Evidence index

- [Game profile integration and reconnect](archive/GAME_STREAMING_PROFILE_TESTS.md).
- [Windows connection preference](archive/WINDOWS_CONNECTION_TESTS.md).
- [Fast-write and timer comparisons](archive/WINDOWS_TRANSPORT_PACING_TESTS.md).
- [Public-client streaming and chunk-size comparison](archive/STARFALL_STREAM_TESTS.md).
- [Public-client lifecycle, PNG and GIF](archive/PUBLIC_CLIENT_TESTS.md).
- [Protocol evidence ledger](archive/PROTOCOL.md).
- [Library, GIF capacity and endurance checks](archive/LIBRARY_PANEL_TESTS.md).
- [Grouped-pixel findings](archive/GROUPED_PIXELS_TESTS.md).
- [Negative pipeline experiment](archive/PNG_PIPELINE_TESTS.md).
- [Resident playback trigger and mixed-region investigation](archive/PROGRAM_REGIONS_TESTS.md).

Historical reports retain their original test conditions and counts. Do not
combine measurements across different hosts, profiles or workloads as a single
benchmark. Twelve fps is a scheduled upload target, not a physical refresh claim.

Raw captures, downloaded artwork and local reference checkouts are private.
Completed material is compressed with file hashes under `archive/private/`;
see [recovery instructions](development.md#private-archives).

## Micromaze seam timing follow-up, 2026-11-22

The owner confirmed two-panel Micromaze works but reported a visible delay
between panels while moving. Existing capture
`captures/wall-ui-20261119-195842-176788.jsonl` contains 148 completed canvases:
the mean wall reply was 233.5 ms, and panel 1's replies trailed panel 2 by a
mean 146.1 ms. The median absolute difference was 145.2 ms and the empirical
95th-percentile value was 175.2 ms. The preceding 4,139-frame session likewise
had a 145.3-ms median difference. These are host reply timings; they do not
establish the physical display offset or that replies follow LED onset.

An opt-in timing alignment mode now uses recent upload durations to delay
faster panels, capped at 250 ms. Synthetic 225/80-ms links verify that after
three warm-up frames it reduces the simulated completion gap from 145 ms to
zero while retaining a 225-ms canvas cycle. Tests also cover disabling and
reenabling it live, ignoring isolated outliers, adapting when the slower panel
changes, bounded delays and cancelling a delayed sibling after failure.
The following owner-observed test established a visual improvement for a
synthetic pattern. Timing during actual game movement remains to be compared.

## Visible synchronization comparison, 2026-11-22

Private capture `captures/visible-sync-observation-20261122T192829Z.jsonl`
compares ordinary PNG streaming and live timing alignment over the same two
connections. Both panels receive identical GO0-GO3 images, changing every
700 ms through the production wall streamer (10-fps ceiling). This is a
transition-timing test, not a game-throughput benchmark. The native GIF uses
the same four decoded images and 700-ms frame durations; its SHA256 is
`7fa6d8cc2126068626316f694109c85aed713ba70849d9b65b2787d62e81d99a`.

The owner saw the bottom panel change first with ordinary streaming. After
enabling alignment, the owner reported matching transitions both by eye and
when reviewing an iPhone 240-fps recording. No visible offset was reported
in that review; individual onset frames were not independently measured.
This supports the option's visual benefit under these conditions, without
establishing exact simultaneous LED onset or a sub-frame error bound.

Excluding the first four canvases in each mode, ordinary streaming completed
182 canvases with a median absolute ACK-completion gap of 129.9 ms. Aligned
streaming completed 163 canvases with a 9.9-ms median gap and a median added
bottom-panel delay of 131.8 ms. These are host reply measurements, separate
from the owner's video observation. The same connections remained open
through the toggle. All completed PNG canvases passed strict image-reply
validation. The research helper and verbatim observations are retained as
`.research/visible_sync_observation.py` and
`.research/panel-capabilities/visible-sync-owner-observations.json`.

For the native comparison, the streamer was stopped after draining its current
canvas. Each panel received the same GIF through the previously verified preview
path, followed by concurrent 15-byte restart writes
`0f0003000031090000397eaf3f0265`. Both returned `0500030003`, and no further
frame uploads or restart headers were sent. The owner reported that the bottom
panel leads. Its physical offset was not measured, and this observation does
not establish whether the lead grows with playback duration. Host restart
submission skew was 0.222 ms; GATT write-completion skew was 20.146 ms. Neither
quantity measures LED onset or isolates the source of the visible offset.

Thus the aligned PNG stream had the best observed visible synchronization in
this comparison. Native loops remain autonomous and closely coordinated in
earlier observations, but concurrent restart is not a verified simultaneous
display swap. The helper finished normally and disconnected both links, leaving
the native loops playing for subsequent cadence/drift investigation.

## Native cadence and drift follow-up, 2026-11-22

Before replacing the four-frame 700-ms GIFs from the synchronization comparison,
the owner reported that the bottom panel still had about the same small lead.
The observation was recorded approximately nine minutes after the concurrent
restart, with no intervening frame uploads or restart commands. This is a
qualitative absence of obvious growing drift over that interval, not a measured
clock error or long-term synchronization guarantee.

A subsequent cadence experiment uses identical 20-frame numbered images (00-19)
with a moving bar. Only their GIF frame delays differ: 100, 50 or 20 ms, encoding
2,000-, 1,000- or 400-ms loops. Each GIF is 2,881 bytes; the helper checks all
decoded pixels, frame counts and delays, reconstructs the upload header, and
uses the previously verified `0x65` preview/restart path. The bottom panel holds
the 100-ms reference while the top receives shorter-delay files. Both links
remain open, with no further frame/header writes during each held observation.

With the top at 50 ms and bottom at 100 ms, the owner reported that the top runs
about twice as fast. This demonstrates a visible response to differing GIF
frame delays. Absolute playback rate and display of every encoded frame were
not established by that ratio alone.

At 20 ms on top versus the same 100-ms bottom reference, the owner selected
"Another ratio / uneven playback". In slow-motion review, the top started at
00 while the bottom was at 01; by the bottom's next 00, the top had completed
three loops and reached 03. Interpreting those as three full loops gives
63/19, or approximately 3.32 top frame intervals per bottom interval, rather
than the requested ratio of five. This suggests an effective delay near 30 ms
if the 100-ms reference runs at its encoded speed. Absolute timing was not
provided, so this count alone establishes neither an exact 33-fps rate nor a
firmware frame-delay floor.

The direct comparison then put a 30-ms GIF on top and a 20-ms GIF on the bottom
(encoded loop durations 600 and 400 ms). Both files decode to the same 20
images, with only their frame delays changed. The owner first observed top15 /
bottom00 in two recordings a minute apart. Those endpoint phases alone cannot
exclude different numbers of complete loops. Asked to check one continuous
bottom 00-to-00 interval in the same clip, the owner confirmed: "yeah. they
keep pace". Thus requesting 20 ms gave no observed loop-speed advantage over
30 ms in this comparison. This supports an effective minimum delay near 30 ms
for this fixture/path, consistent with the earlier approximately 3.32 ratio.
An exact 33-fps physical rate, universal firmware cap, individual-frame
completeness, and timing under more complex GIF workloads remain unmeasured.

The 30-ms/20-ms comparison is in
`captures/native-cadence-observation-20261122T194733Z.jsonl`; its 30-ms file
SHA256 is `d3de78ce37580bff33569795c90b78a42f3931af9ade413ae0ffce415312fff5`.
Both helpers finished normally and disconnected without exit-mode commands,
leaving the last native loops playing. All uploads and restarts passed their
strict GIF-reply checks; no frame uploads or restart writes occurred during
the held observations. No production code was changed for this follow-up.

Private capture: `captures/native-cadence-observation-20261122T194144Z.jsonl`.
Fixtures, their SHA256 hashes and exact restart headers are recorded in the
capture's experiment row. The reproducible helper is
`.research/native_cadence_observation.py`; verbatim owner observations are in
`.research/panel-capabilities/native-cadence-owner-observations.json`.

## Native display controls follow-up, 2026-11-22

The top-panel-only survey uses the same native GO0-GO3 preview GIF as the
synchronization experiment. The bottom panel is untouched. Exact five-byte
brightness, on/off and orientation packets were checked against the installed
upstream builders and the Android `BaseSend` implementations. The helper is
`.research/native_controls_observation.py`; private capture:
`captures/native-controls-observation-20261122T200518Z.jsonl`. Verbatim visual
reports are in `.research/panel-capabilities/native-controls-owner-observations.json`.

- Brightness values 10 and 50 alternate visibly while the native animation
  continues. Tested packets are `050004800a` and `0500048032`, both replying
  `0500048001`. This does not measure optical brightness or the full value range.
- Display-off `0500070100` makes only the top dark; display-on `0500070101`
  brings back moving GO0-GO3 without an upload/restart. This does not distinguish
  hidden continued playback from pausing or restarting. Both controls reply
  `0500070101`.
- Orientation1 (`0500068001`) produces a 180-degree view, with the colored bar
  on the right and text upside down. Values 2 and 3 also leave that view after
  separate orientation0 reset commands. Animation continues at value3. The
  transient resets were not separately confirmed visually. At final cleanup,
  the owner confirmed that orientation0 restores the upright view. Replies are
  `0500068001` for all tested orientation values. These observations do not
  establish four distinct rotations on this panel.

The top was then set to orientation1 and brightness10, disconnected, and
reconnected with only the eight-byte type/time query and four-byte version
query. No settings, GIF upload or restart header was resent. The owner reported
an upside-down B0/B1 GIF that "looks dimmed": orientation persisted and dim
brightness was still apparent, but the temporary GO preview had changed to
previously saved B0/B1 content. The exact triggering step (disconnect, reconnect
or identity query) is not isolated. Do not describe the GO preview as having
survived that exchange.

With Bluetooth disconnected and without opening the phone app, the owner
removed USB power from the top for approximately five seconds and restored it:

- The intro animation played upside down, then saved A0/A1 and B0/B1 played
  upside down, cycling between the two. Thus orientation1 persists through
  power loss and affects startup as well as resident media.
- Asked about brightness before any further commands, the owner confirmed
  "Still looks dim". This supports brightness10 retention qualitatively, without
  an optical measurement or setting readback.
- The two original slot1/2 GIFs survived and automatically played as a playlist.
  No media upload or slot-selection command was sent during the power-cycle
  observation. Per-slot selection after power loss was not separately tested.

For display-off retention, a fresh connection sent only identity/version queries
and `0500070100`, then disconnected without further display writes. The owner
power-cycled the top again and reported "Intro / playlist appears again".
Soft display-off therefore does not persist across this USB power cycle.

Cleanup reconnected, queried identity/version, set on / orientation0 /
brightness50, and disconnected. The owner confirmed "Yes—upright, brighter,
and playing". This restores a known baseline; original brightness was not read
before testing. The helper finished normally with no recorded errors. Only one
GIF preview was uploaded in this survey; later phases sent controls and identity
queries, with no saved-slot writes or deletion. The bottom remained untouched.

## Headless web preview and initial Ubuntu check, 2026-11-22

The first service/browser slice uses the existing wall worker without importing
Tk. Synthetic service/API tests cover discovery, saved setup, controller takeover,
stale-input release, browser loss, media limits and worker cleanup. The complete
local suite passes **339 tests, with four experimental PR #88 tests skipped**.
The run uses a fresh workspace temporary directory because the default Windows
pytest temporary/cache paths were inaccessible in this execution environment.

A real Chromium smoke test with simulated Bluetooth exercised two-panel setup,
connect, demo selection, game input, blur/pause and a second browser taking
control. Desktop and mobile viewport screenshots were inspected; no horizontal
overflow or browser page errors were reported. This is not iPhone Safari or
physical LED validation.

A wheel was installed in a new virtual environment on the owner's Ubuntu x86_64
host (kernel 6.8.0-149, Python 3.12.3, BlueZ 5.72, Intel USB adapter 8087:0aa7).
It fetched the pinned, unmodified pypixelcolor revision and started the bundled
web service without a source/research checkout. LAN HTTP and discovery of both
known panels succeeded. No system service installation was performed.

Linux playback is **not yet validated**. Connections intermittently expose an
empty GATT collection or only AE00, including in standalone Bleak processes.
The first packet capture also contains one complete discovery of FA00/AE00 and
an MTU 517 exchange. In the failing discovery, a Find Information request for
0x0007 receives Invalid Handle referring to 0x0087; the expected FA service is
then unavailable to the application. A later connection exposes FA02/FA03 but
the initial device-information write returns Invalid Handle. These are observed
wire/API outcomes, not an established firmware or host-stack root cause.

The private trace is `linux-gatt.btsnoop` in the isolated preview directory on
the Ubuntu host; its decoded copy is `.research/linux-gatt-btmon.txt`. Do not
describe this as working Linux wall output or bypass service validation/retry
partially sent media to conceal the failure. The adapter
now reports an empty host service result explicitly and closes the connection.

### Ubuntu independent-tool comparison, 2026-11-22/23

The second capture catches an acknowledged FA02 write request to handle 0x0006
receiving Invalid Handle referring to 0x0086. Notification configuration writes
to 0x000a sometimes fail with a reference to 0x008a as well. A direct gatttool
version-query write succeeded once, but that tool reports only the ATT write
result; this does not verify receipt of the application version reply or playback.

More decisively, repeated gatttool reads of handle 0x0003 on a single connection
alternate between the expected `LED_BLE_D121302F` name and bytes `10840002ae`,
which match the declaration at handle 0x0083. Explicit reads of 0x0083 also return
those declaration bytes. The same ten name reads using Windows Bleak return
the correct name ten times. This comparison bypasses our service, pypixelcolor
and, on Linux, Bleak. It does not isolate the adapter, its firmware/driver or a
panel interoperability defect, nor prove where any bit is changed.

On 2026-11-23, ten Linux name reads gave five correct names and five declaration
values. With no other Bluetooth devices connected, `bluetoothctl power off`
and `power on` both succeeded. Ten subsequent reads gave six correct names and
four declaration values. Thus this adapter power toggle did not resolve the
problem. No display media or settings were sent in this comparison.

The owner subsequently unloaded and reloaded `btusb`. The kernel reported that
the Intel device was already patched (patch 0x43); this was not a fresh firmware
load. Ten more name reads again gave six correct names and four declaration
values. Driver reload therefore did not resolve the problem either. No spare
Bluetooth adapter is available for the proposed comparison.

Before the owner paused work, the Windows headless service connected both panels,
verified their dimensions and received strict completion replies for identify
and 20 subsequent ring-demo frames through the HTTP/WebSocket application API.
The saved result is `.research/panel-capabilities/windows-web-live-result.json`.
The sample at frame 21 reports 204.283/91.895 ms upload durations, a 113.093 ms
bottom-panel delay and 4.862 ms completion skew. These are transport timings,
not measured optical synchronization. Visual confirmation and physical iPhone
browser testing are still pending. On pause, both Windows BLE connections were
closed and the Windows and isolated Ubuntu preview servers were stopped.

The host reports Intel legacy ROM 2.x revision 5.0, firmware
`intel/ibt-hw-37.8.10-fw-22.50.19.14.f.bseq`, activated patch 0x43, and Ubuntu
linux-firmware `20240318.git3b128b60-0ubuntu2.26`. The 2026-11-23 decoded trace is
`.research/linux-gatt-followup-20261123.txt`; the previous write-test decode is
`.research/linux-gatt-followup.txt`. The remote follow-up capture filename was
reused by the owner, so these are distinct runs. A second-adapter comparison is
the next hardware isolation step; general Linux compatibility remains unproven.

## Windows web and standalone preview, 2026-11-23

Further Linux Bluetooth testing was deferred at the owner's request. Windows
work continued with the headless service, phone interface and a local standalone
build. The owner confirmed that the iPhone page opened and that Micromaze ran
on the panels and responded to the phone controls.

Direct LAN access to the Windows host timed out from both iPhone and Minifig.
Windows reported MpsSvc in StopPending; an attempt to add a narrow private-LAN
application rule failed with Windows error 1753. No successful firewall change
is claimed. For the phone test only, a temporary SSH loopback reverse forward
and aiohttp relay on Minifig provided HTTP/WebSocket access to the Windows
service. Minifig did not own the BLE links. This private test relay is not
shipped or required by the application; normal direct LAN access still requires
a functioning host firewall/network configuration. It also forwards the
authentication close code and generates a QR for its reachable address.

Phone setup now accepts the short host address plus a six-digit per-start code.
Pairing exchanges it for the longer session token. Five failed guesses in one
minute temporarily block code exchanges. QR and address/code details require
authentication. Tests cover pairing, origin checks, rate limiting and protected
QR access. Browser smoke assertions pass for code login, QR loading, mobile
sizing, controller takeover and input/blur handling. On Windows the smoke-test
browser shutdown also logs a Proactor ConnectionResetError; no browser page
error or failed assertion was reported.

The complete suite passes **344 tests, with four PR #88 experiments skipped**.
Synthetic worker/game integration now covers one-, two- and three-panel layouts.
The web editor explains that one panel is a standalone display, multiple panels
form a shared canvas, and larger-than-two configurations are experimental. The
existing limits of 16 tiles and 512x512 bound layout size, not physical Bluetooth
capacity. Setup controls are disabled while connected to avoid unsaved edits
that cannot yet be applied live.

A fresh virtual environment installed the built application wheel and the exact
unmodified upstream Git commit. PyInstaller 6.22.3 / hooks 2026.10 produced a
Windows x64 onedir ZIP with CPython 3.13.9, frontend, timezone data, dependency
notices and build manifest. WinRT runtime is 4.2.0 in this bundle (4.1.0 in the
earlier development environment). Its dependency versions are captured in
`tools/packaging/windows-constraints.txt`. The build rejects editable application
installs or an upstream revision that differs from the pin.

The ZIP was extracted into a separate folder and launched with Python/Git
removed from PATH and no Python environment variables. Code login, bundled UI,
QR generation, all three game simulations, PNG/GIF decoding and user-directory
settings persistence worked. No private settings, captures or research files
were present in the archive. These are checks on this Windows machine, not a
second clean Windows host.

An initial handoff from the development service to the executable completed a
one-panel session but then could not rediscover the bottom panel. Windows still
reported that panel as connected. Both panels appeared in a scan after the old
development process exited; this sequence does not isolate the cause. The final
standalone executable subsequently passed three consecutive sessions: one panel
(64x16), two panels (64x32), and a two-panel disconnect/reconnect. Each session
completed identify plus ring frames with strict final image replies; eight
completed wall frames were recorded per session. This is not a long disconnect
stress test or an optical timing measurement. The current standalone instance
was left playing the two-panel ring through the same phone relay.

Private evidence: `.research/panel-capabilities/standalone-windows-live-results.json`
and captures under the acceptance profile. The build's original media/game
assets are rendered locally; downloaded research artwork is not included.

Local artifact:
`dist/windows-preview-flexible/LED-Wall-Windows-x64-0.1.0-preview.zip`.
SHA256: `8247c17f558cd248b4b3ddd3c1ba10441fc913aa898277dcf9acc9f3a418a6f1`.
Application wheel SHA256:
`004cc50674ff5b89e443ba0a1aa554515a8e6d2275f2ec5da87efcbb43f646e4`.
The unsigned ZIP is a local preview, with public release and
the remaining roadmap acceptance checks still outstanding. Linux remains
unvalidated; no new upstream PR or public release was created.

### Individual panel controls, 2026-11-23

Each saved panel now has visible Connect, Disconnect and Remove buttons during
playback. Disconnect preserves its mounting position and persists an exclusion;
Remove forgets it. A card's Connect from idle starts that panel alone, or adds
it to an already running wall. The global Disconnect all closes the session.
The worker is joined and replaced when changing its panel set, briefly
reconnecting the remaining panels. Active coordinates use their bounding box;
games reset without starting and uploaded media must be loaded again.

The complete suite now passes **350 tests, with four PR #88 experiments skipped**.
New coverage includes single-panel idle connect, exclusion persistence alongside
timing preferences, remaining-panel sizing, last-panel disconnect/removal,
invalid requests, ownership and HTTP/WebSocket state. Chromium checks exercise
these controls during playback, mobile sizing, and updates in a second browser.
Assertions pass; Windows Proactor shutdown warnings remain as noted above.

The rebuilt standalone passed real Bluetooth checks for: initial two-panel
streaming; disconnecting TOP with BOTTOM rendering at 64x16; adding TOP back;
removing BOTTOM with TOP rendering at 64x16; and restoring the original two-panel
layout. Each step completed at least three strict-reply wall frames. Both panels
were left running the ring. Private evidence:
`.research/panel-capabilities/panel-controls-windows-live.json`.
The existing phone relay serves the updated assets, accepts the new per-start
short code, and publishes connected two-panel WebSocket state.

Updated local artifact:
`dist/windows-preview-panel-controls/LED-Wall-Windows-x64-0.1.0-preview.zip`.
SHA256: `feaa73a020a218a8cf587767797ca10e08bd53774dd5d9b0229ece120c024387`.
Application wheel SHA256:
`34d8cf2563763564b8c928036b4177bdd3d9b6c2d4fe80307febe8c5d562af26`.

### Community documentation and packaging cleanup, 2026-11-23

A new virtual environment installed the declared development/server/game extras
and an ordinary wheel of the exact pinned upstream commit, without the private
editable research checkout. The complete suite passed **350 tests, four optional
PR #88 cases skipped**, under Python 3.13.9 / pytest 9.2.0. This establishes an
isolated dependency install on the same Windows host, not another clean PC.

The owner selected MIT. Project metadata and the wheel include the license;
the new standalone includes `LICENSE.txt`, updated first-use/limits text and
dependency notices. Extracted startup, clean settings, bundled UI, short-code
pairing, QR generation, WebSocket control and software demo checks passed with
Python/Git removed from PATH. An initial smoke helper needed correction to
accept binary preview messages alongside JSON state; the corrected check passed.
No Bluetooth connection was opened by this cleanup check. The previous build's
one/two-panel and individual-control observations remain the physical evidence;
the running service was not replaced.

New local artifact:
`dist/windows-preview-community/LED-Wall-Windows-x64-0.1.0-preview.zip`.
SHA256: `aa60ae0d4a05b9f51e71a659c23c3d3b369b82dde39873885b7860e6c883f273`.
Application wheel SHA256:
`d038a9dfe6a3bb9407ac7df71af0d1cc72a672cb23efdcc2dd4a47374056bb2c`.
No public release or new upstream PR was created.

Recent single-panel logs also support the reported speed asymmetry: the top
session had median upload/reply time 224.5 ms over 255 completed frames, while
the bottom session had 108.6 ms over 482. Their image sequences were not matched,
so this is not a controlled same-workload benchmark. Read-only Windows snapshots
on the separate active sessions both reported a 22.5-ms interval and peripheral
latency zero. That rules out explaining those observations solely by a different
reported interval; it does not isolate radio scheduling, image processing,
write-completion timing or panel acknowledgement behavior. The optional desktop
Windows throughput hint has not been integrated into the web/wall worker.

Internal cleanup/publication records are retained privately; technical evidence
and current verification remain in this report.
Current-file redaction does not remove the addresses from earlier Git commits;
the prepared public source snapshot excludes Git history and private artifacts.

## Automatic native wall GIF playback, 2026-11-24

The desktop wall and browser media upload now use Pillow to fit the complete
canvas, split around bezel gaps, undo mounting rotation and encode a native
64x16 GIF per panel. The production worker uploads these with the verified
temporary 0x65 preview destination, validates each GIF completion, then sends
the corresponding restart headers concurrently. Native playback sends no
ongoing PNG frames. Pause publishes a snapshot; Play uploads/restarts the loop.

Hardware capture `captures/wall-ui-20261124-215936-995943.jsonl` records two
connected panels on a 64x35 canvas with a three-pixel gap. The smooth vortex
source contains 660 frames at 30 ms, a 19.8-second loop; the prepared panel GIFs
are 593,900 and 599,731 bytes. Upload and restart completed in 69.86 seconds,
passing strict `0500030003` completion checks on both panels at both stages.
The log then remains at `native_playing`, with no subsequent frame uploads.
Source SHA256: `8303f470c70b5b1646e59d35d212b51e99b6abe5b6b17507602d7b7baa9f19be`.
This verifies the larger multi-window preview/restart transport through the
production worker, not exact optical FPS, frame completeness or seam timing.

Automated validation: 368 passed, four existing isolated-PR skips. New cases
cover fitted crops, hidden gap pixels, all mounting rotations, common loop
timing with a static panel half, fast-source sampling, GIF transparency/disposal,
multi-window lengths/CRC/restart headers, upload/restart barriers, failures,
superseded requests, no ongoing native writes, desktop pause/refit/restart and
browser media upload/playback transitions. Browser JavaScript syntax also passed.
