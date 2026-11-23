# Investigation checkpoint: 19 November 2026

Investigation stopped for the evening at the owner's request. This file collects
the current conclusions and a starting point for the next session. Packet-level
evidence and qualifications remain in the linked reports.

## Working wall setup

Two 64x16 panels work as one PC-controlled canvas. Cyan panel 1 is physically
above orange panel 2. With no compensation the canvas is 64x32; the current
three-pixel bezel compensation puts the bottom panel at Y=19, making it 64x35.
Hidden rows are omitted from uploads. Position, mounting rotation and the gap
are adjustable; the saved layout remains local in `.state/wall-settings.json`.

The [wall controller](../../games/wall/README.md) provides identify labels, the ring
seam demo, whole-canvas Snake, and image/GIF playback with Fit, Fill and Stretch.
Snake currently requires a rectangular layout without gaps or compensation.

Our controller adds layout and coordination on top of the pinned pypixelcolor
command builders and transport. Each panel has its own BLE link. Both halves
of a canvas are uploaded concurrently, then the sender waits for both PNG
completion replies. It takes the latest available frame rather than building
a queue of old game states. This is software coordination; it does not establish
an atomic display swap or a shared refresh clock.

Only two simultaneous physical panels have been verified. The editor's
16-panel limit is software policy, not a measured Bluetooth capacity.

## GIF playback and synchronization

There are two distinct playback paths:

- The wall controller decodes a GIF on the PC, fits it to the virtual canvas,
  splits each frame and streams RGB PNGs. The three-pixel gap can therefore be
  included in the source geometry. The PC must keep running. The wall targets
  at most 10 canvas updates/s and can skip superseded frames.
- Native GIF uploads play autonomously on a panel after disconnecting. A
  4,096-frame, 1,915,364-byte GIF played successfully; that is a tested lower
  bound, not a capacity ceiling. One small slot-1 GIF survived one power cycle.
  Physical playback FPS and general storage limits remain unmeasured.

The APK revealed a 15-byte header that restarts a compatible, already uploaded
GIF. Repeated headers prevented the diagnostic from reaching its later frames,
confirming restart behavior. Sending one header to each panel concurrently
brought deliberately offset GO0-GO3 loops into close visible alignment. The
owner observed a small, steady bottom-panel lead. Uploads started playing before
the header, so deferred start was not demonstrated. This native mechanism is
not integrated into the wall controller. See the
[capability map](../panel-capabilities.md#newly-found-two-panel-path-and-its-limits).

## Commands established, negative results and open questions

| Family | Current finding |
| --- | --- |
| RGB PNGs | Verified full-frame live output and the current game path. Indexed PNGs failed visually despite a completion reply. |
| Native clock | Top panel showed green time, a blinking colon and an animated character. Minutes advanced after BLE disconnect. |
| Native grouped drawing | Static same-color groups work, including a complete native two-square baseline. Earlier grouped animation did not beat PNG throughput. |
| Resident playback | `060007800100` triggered scrolling text starting with "I'm in a hurry", followed by other text and the boot image, without uploading that media. Factory content versus earlier app installation is unresolved. |
| Resident button selection | Button 2 also triggered scrolling, but the owner did not confirm different content. Arbitrary selection of our own cached animations remains unverified. |
| Program list | `07000880010001` returned `0500088001` but left BASE visible. The app uses this command before uploading selected programs; a reply alone is not a playback-switch result. |
| Native score/countdown/stopwatch | Tested sequences left TEST or showed the default image. Correct counters were not demonstrated. |
| Preserve/overlay | Entering DIY mode 3 and painting a square did not preserve the preceding PNG background. The sequence did not isolate which step hid it. |
| Mirror/movement | Tested horizontal mirror and right-movement commands produced no confirmed swap or shift, including on a fully native baseline. Other states/parameters remain open. |
| JPEG frames | Recovered camera/game framing elicited a reply but displayed the boot image. Correct JPEG rendering is unverified. |
| Mixed regions | The APK has a native container with separate text/image descriptors and coordinates. A candidate two-region preview showed the boot image. Image-kind assignment and entry requirements remain unresolved. |

The business-remote code assigns custom content serials beginning at 111 before
uploading it, but we have not established how those banks map to button commands
on these panels. The native region path uploads a whole template; no independent
resident-region replacement command was established. See the
[program/region report](PROGRAM_REGIONS_TESTS.md) and
[full capability map](../panel-capabilities.md).

## App, hardware identity and firmware research

Both panels report type `0x83`, MCU 14.02 and Bluetooth 7.04. Their advertising
selector is customer `0007`, product `04`.

The vendor's Android 3.8.0 APK has protected application code. The readable 3.7.9
reference build has a matching extracted signing-certificate fingerprint and
enabled the command survey. This is not independent full signature validation.
Its active Android picker excludes `0007/04` from dual-eye connections. The
owner separately observed the iPhone picker disconnecting one panel when the
other is selected. The packaging's "Double fun mode" remains unexplained;
neither the packaging nor these picker observations establish firmware pairing.

Authenticated queries on both AE00 services confirmed JieLi RCSP protocol 2.0.
The identity replies are sparse, and feature-map replies contain no bitmap.
The exact chip model and additional hardware interfaces remain unidentified.
The actual firmware metadata request was recovered, but four bounded requests
returned no matching data and no firmware image. This does not establish that
14.02 is the latest available firmware. Details:
[APK](../apk-investigation.md), [AE00](../ae00-identification.md),
[firmware metadata](../firmware-metadata.md).

## Performance evidence and its limits

A 244/500/500/244-byte chunk comparison sent the same 57 ring frames in each
block over two open connections. All 228 canvases, or 456 panel uploads,
completed successfully. Larger acknowledged chunks reduced the number of writes
but did not establish a consistent speed improvement. The wall already requests
500-byte chunks, and no transport change resulted from this comparison.

This later run completed about 4.6-5.2 canvases/s. In the first three blocks,
median upload completion was about 195 ms for the top and 80 ms for the bottom.
Earlier runs were faster. We have not isolated a permanent panel difference:
connection timing or scheduling established during a session remains plausible.
These are host upload timings, not LED refresh, input-to-photon latency or a
hardware FPS ceiling. The 10-fps wall target is likewise a software limit.
See [validation](../validation.md) for the different test conditions.

## Resume point

No further hardware investigation is scheduled tonight. The wall controller
was restored and both panels resumed acknowledged ring-demo uploads.

For the next session, the most useful unresolved capability question is whether
our own preloaded animations can be selected by small commands. Trace the custom
remote-bank mapping and content provenance before choosing a test fixture.
For regions, resolve the image-kind assignment and exact model/entry path before
interpreting another failed preview as lack of support. If interactive-game
performance becomes the priority, compare reversed connection order, each panel
alone and fresh connections before attributing the timing difference to hardware.

Raw BLE captures, downloaded APKs, disassembly, research helpers, device settings
and generated fixtures remain in the existing ignored local directories. Source
and reports are versioned; the reports retain original private artifact paths.

Evening checkpoint validation: the full source suite passed 288 tests, with four
optional PR-branch cases skipped. These tests use synthetic BLE objects and did
not restart hardware investigation.

## Follow-up: cached selection, 22 November 2026

The remaining cached-selection question now has a positive result. Two original
GIFs in ordinary slots 1/2 switched A/B/A using seven-byte `show_slot` commands,
without re-uploading either file. B was also recalled on a fresh Bluetooth
connection using only identity/version queries and its slot-selection command.
The same selector left the HOLD PNG unchanged in the preceding experiment:
selection worked in the tested native GIF context, not after that PNG override.
Custom remote banks 111/112 could be uploaded and displayed, but their later
selection remains unresolved. Two-file power-cycle retention was not tested in
that sequence; the later native-controls survey below verified it.
The [program/region report](PROGRAM_REGIONS_TESTS.md) records the exact
packets, original GIF hashes, owner observations and captures. This follow-up
supersedes the earlier unresolved claim about ordinary cached-GIF selection;
the dated 19 November checkpoint above is retained as history.

## Follow-up: visible streaming alignment, 22 November 2026

With identical GO0-GO3 transitions every 700 ms, the owner saw the bottom panel
update first during ordinary streaming. Enabling the existing timing-alignment
option on the same connections made the transitions look simultaneous, including
in the owner's review of an iPhone 240-fps recording. Exact LED onset was not
independently measured. This verifies a visual improvement for the test pattern;
actual game movement and consistency across new connections remain separate
questions. The [validation report](../validation.md#visible-synchronization-comparison-2026-11-22)
records the capture, conditions and separate host reply measurements.

The same test images were then uploaded as native GIFs and restarted concurrently
with their 15-byte headers. Both restarts were acknowledged, with no further
frame/header writes during observation. The owner still saw the bottom panel
lead. Aligned streaming therefore gave the best observed synchronization in
this comparison; native restart is useful coordination but has not established
an exact simultaneous display swap. Both links were disconnected with the
native GIFs left looping; the follow-up below adds cadence/drift observations.

## Follow-up: native cadence and drift, 22 November 2026

The owner reported about the same small bottom-panel lead when checked roughly
nine minutes after the GO-loop restart. No intervening uploads or restart
commands were sent. This is no obvious growing drift over the observed interval,
not an exact clock-accuracy measurement.

For identical 20-frame counters, a 50-ms-per-frame GIF ran about twice as fast
as a 100-ms reference. A 20-ms request instead gave approximately 3.32 times the
reference speed in the owner's slow-motion count, rather than the requested
five times. A direct 20-ms/30-ms comparison then kept pace over a continuous
loop in the owner's review. These results support an effective minimum delay
near 30 ms for this GIF path. Approximately 33 fps is a hypothesis conditional
on the timing reference, not a measured absolute rate or universal ceiling.
Every-frame display and more complex GIF workloads remain unmeasured. The
[validation report](../validation.md#native-cadence-and-drift-follow-up-2026-11-22)
preserves the counts, interpretation limits, fixture hashes and both captures.
Both links are disconnected, with top30-ms / bottom20-ms loops left playing.

## Follow-up: native display controls, 22 November 2026

Top-only testing verified brightness10/50 changes while native animation runs,
display-off blanking, and display-on returning to moving animation without an
upload/restart. Hardware orientation0 restores upright; values1/2/3 each showed
a 180-degree view in the tested sequences. They are not four verified rotations.

Orientation1 and apparent dim brightness survived an identity-only reconnect
and a USB power cycle. The reconnect sequence changed temporary GO preview to
saved B0/B1 with no media upload; which step triggered the change is unresolved.
After USB power loss, the owner saw the upside-down intro, then both original
saved A/B GIFs automatically cycling as a playlist. This also verifies two-file
power-cycle retention. Per-slot selection after power loss was not retested.

Soft display-off did not persist across a second USB power cycle: the intro and
playlist reappeared. Brightness retention is qualitative; no setting readback
or optical measurement was made. These results concern the tested top panel
and values, rather than every parameter or both units.

The [controls report](../validation.md#native-display-controls-follow-up-2026-11-22)
records exact commands, replies, observations and capture references. The helper
finished normally, set top on / upright / brightness50, and disconnected. The
owner confirmed the final upright, brighter, playing state. The bottom was
untouched throughout this survey. No further hardware test is running; the
owner intends to choose a new direction after this completed controls survey.
