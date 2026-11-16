# Protocol evidence ledger

Last updated: 2026-11-14. BLE advertisements, GATT metadata, information replies,
pixel/corner tests and image-upload experiments have been recorded. The owner
visually confirmed pixel control, 64×16 orientation and a full diagnostic PNG
rendered from Python without the phone app.

## Owner-reported hardware

| Field | Evidence/status |
| --- | --- |
| Brand and label | Owner: B.K. Light, `3226274 | 37/2026` |
| Official app | Owner: iPixel Color |
| Resolution | Original brief: unverified 16×51; hardware type and owner-observed corners now verify 64×16 |
| Power | Brief states 5 V USB; adapter rating to be recorded |
| Dual-panel mode | Advertised in brief; topology and synchronization unverified |

`37/2026` is recorded literally; its meaning has not been established.

## Confirmed on our unit

Owner-operated on/off/on comparison strongly identifies the named `LED_BLE_*`
advertiser as our panel, establishing BLE advertising. Its identity is recorded
in private scan files. Windows reports connectable/scannable advertisements and
a public address type. No advertised service UUIDs were present. Metadata-only
GATT inspection succeeded at **17:18:51 UTC / 18:18:51 CET** after the owner moved
USB power to the PC. The successful capture is
`captures/gatt-pc-usb-20261114.json`. This does not establish the cause of the
earlier failures or imply a USB data connection; communication was BLE.

| Service | Characteristic | Properties | Bleak-reported handle |
| --- | --- | --- | --- |
| `00001800-0000-1000-8000-00805f9b34fb` | `00002a00-0000-1000-8000-00805f9b34fb` | read | 2 |
| `000000fa-0000-1000-8000-00805f9b34fb` | `0000fa02-0000-1000-8000-00805f9b34fb` | write, write-without-response | 5 |
| `000000fa-0000-1000-8000-00805f9b34fb` | `0000fa03-0000-1000-8000-00805f9b34fb` | notify | 8 |
| `0000ae00-0000-1000-8000-00805f9b34fb` | `0000ae01-0000-1000-8000-00805f9b34fb` | write-without-response | 129 |
| `0000ae00-0000-1000-8000-00805f9b34fb` | `0000ae02-0000-1000-8000-00805f9b34fb` | notify | 131 |

FA03 has a `2902` notification configuration descriptor (reported handle 10).
AE02 also has one (133). No value reads, subscriptions, pairing requests,
handshakes or application writes were performed by the inspection. AE00's
function is unverified on our unit; its characteristics were not exercised.
Resolve ATT handles from the actual connection/capture rather than assuming
that these Bleak-reported handles transfer to the phone connection.

The grid is now **64×16**: the hardware returned type `0x83` (64×16 in the
references), and the owner confirmed all four proposed corner markers at the
physical edges. `(0,0)` is top-left, x increases to the right and y downwards in
the observed orientation. This supersedes the brief's unverified 16×51 figure;
the original brief is preserved unchanged.

The information query returned MCU version components `[14, 2]` and secondary
version components `[7, 4]`. These are recorded as raw pairs; their release/version
naming and the secondary controller's function have not been independently proved.
The controller chipset, general acknowledgment semantics, brightness commands,
persistent animation slots and maximum frame rate remain unknown. RGB ordering for
the tested pixel command is visually confirmed below.
BLE support is confirmed; additional Bluetooth Classic support is unverified.

## Candidate family, not a device specification

The iPixel Color app name and now-observed FA service/characteristic properties
support the FA-family hypothesis. The
[B.K. Light Python reference](https://github.com/Pupariaa/Bk-Light-AppBypass/blob/f83b90e9a8229d3c3bfca9568733c1f15afc795c/bk_light/display_session.py)
uses write `0000fa02-0000-1000-8000-00805f9b34fb` and notification
`0000fa03-0000-1000-8000-00805f9b34fb`. The
[Web Bluetooth reference](https://github.com/mx2rel/BK-Light-LED-rx-engine/blob/a5a1bfd201081a4ddf2ed012f11c36eb7e40e9d8/matrix.js)
selects service `000000fa-0000-1000-8000-00805f9b34fb`.
These are comparison fingerprints, never hard-coded into our discovery tools.

Source-level candidate formats and their limits are in [RESEARCH.md](RESEARCH.md).
Shared UUIDs, app branding and retailer were insufficient to confirm packet
semantics; subsequent pixel and information operations now have direct evidence.
The information exchange also sets the panel clock, so it is an explicit write
experiment, not part of read-only discovery. No blind initialization sequence
is sent by the tooling.

## Promoting a field to confirmed

Record the capture filename, UTC time, experiment ID, direction, characteristic
UUID and resolved ATT handle, packet bytes/length, response and visible effect.
Keep observed byte values separate from interpretations. A notification is not
automatically an acknowledgment; a successful GATT write is not proof of rendering.
Repeat the experiment with one variable changed. Preserve firmware/model context.

| Experiment | Capture/time | Observation | Interpretation | Confidence |
| --- | --- | --- | --- | --- |
| On/off/on discovery | Private scans dated 2026-11-14 | Named LED advertiser disappears while off and returns at same address when on | Strong target identification, BLE advertising present | Observed |
| Initial GATT attempts | Private diagnostic and empty failed inspection outputs | Device-not-found in sandbox; services unreachable outside sandbox | Failure cause unverified | Observed failure |
| Successful GATT inspection | `captures/gatt-pc-usb-20261114.json`, 2026-11-14 17:18:51 UTC | 00FA with FA02 write/write-without-response and FA03 notify; AE00 also present | Matches candidate iPixel GATT interface, packet semantics not yet verified | Metadata confirmed |
| First pixel, initial run | `captures/pixel-reference-20261114.jsonl`, 17:23:07–17:23:19 UTC | Three GATT writes completed; no FA03 notifications; owner did not watch | Transport success only | Logged; visual effect unverified |
| First pixel, owner-observed repeat | `captures/pixel-reference-repeat-20261114.jsonl`, 17:23:56–17:24:21 UTC | Red/green/blue writes at (0,0), eight-second holds; owner confirmed a corner pixel changed colors | First pixel milestone achieved | Logged writes + owner visual confirmation |
| Device information | `captures/device-info-20261114.jsonl`, 17:33:42 UTC | Type `0x83`; version pairs `[14,2]`, `[7,4]`; negotiated MTU 517 | References map type to 64×16; corroborated next by corners | Reply observed |
| Grid/orientation | `captures/corners-64x16-20261114.jsonl`, 17:34:36–17:34:37 UTC | Twelve pixel writes forming colored corner L markers; owner: all four at expected corners | 64×16, origin top-left, x right, y down | Logged + visually confirmed |
| Static RGB frame | `captures/static-rgb-64x16-20261114.jsonl`, 17:37:22–17:37:25 UTC | 3081 bytes, thirteen sequential chunks; FA03 reply `05 00 00 00 01`; owner saw startup `> LED <` artwork, no diagnostic image | This raw path did not produce the intended image | Logged + observed failure |
| PNG initial attempts | `captures/static-png-64x16-20261114.jsonl`, `captures/static-png-64x16-retry-20261114.jsonl` | Both failed during GATT service retrieval, before application writes | No conclusion about PNG compatibility; owner then power-cycled panel | Connection failures only |
| PNG after power cycle | `captures/static-png-after-powercycle-20261114.jsonl` | Same GATT-unreachable failure before writes | Panel power cycle alone did not resolve this occurrence | Connection failure only |
| Cached GATT diagnostic | `captures/windows-link-after-cycle-20261114.jsonl`, 17:48:42–17:48:48 UTC | Windows access allowed; cached FA-service session connected at MTU 517; zero application writes | Cached enumeration is a useful host workaround here | Observed |
| Successful static PNG | `captures/static-png-cached-20261114.jsonl`, 17:50:20–17:50:22 UTC | 506-byte PNG in 521-byte frame, three chunks, reply `05 00 02 00 03`; owner confirmed border/corners/text/RGB bars | PNG/CRC static upload works on this unit | Logged + visually confirmed |
| Host-streamed sprite | `captures/sprite-2fps-20261114.jsonl`, playback 18:17:22–18:17:32 UTC | 20 PNG uploads at 2 fps in 10.006 seconds, all replied `0500020003`; owner confirmed regular movement and END with no glitches | Bounded PNG host streaming works at the two-metre desk placement with PC antennas | Logged + visually confirmed |
| Numbered sprite at 5 fps | `captures/sprite-5fps-counter-20261114.jsonl`, playback 18:21:41–18:21:51 UTC | 50 PNG uploads with counters 01/50–50/50 in 10.004 seconds, all replied `0500020003`; owner confirmed normal counter progression and END with no glitches | Bounded 5 fps PNG streaming works at the same desk placement | Logged + visually confirmed |
| One-minute sprite at 5 fps | `captures/sprite-5fps-minute-20261114.jsonl`, playback 18:25:59–18:26:59 UTC | 300/300 expected image replies over 60.003 seconds, no retries or connection failures; owner saw all frames but reported possible unequal timing | Minute PNG streaming works at the same desk placement; perfectly uniform rendering is not established | Logged + owner observation |
| Panel-local GIF | `captures/gif-local-20261114.jsonl`, disconnected observation 18:33:28–18:33:40 UTC | One 4088-byte GIF in 4103-byte message, 17 chunks; reply `0500030003`; owner confirmed ongoing looping and steady-looking timing after disconnect | Small GIF local playback works in slot 0 without frame streaming | Logged + visually confirmed |
| Native eyes, two windows | `captures/eyes-44f-10fps-20261114.jsonl`, completed 18:42:14 UTC | 44 frames, 100 ms encoded delay, 20,500 bytes; window replies `0500030001`, then `0500030003`; owner confirmed correct steady motion and repeating counter | Multi-window GIF upload works for this file | Logged + visually confirmed |
| Eyes rate comparison | `captures/eyes-rate-comparison-20261114.jsonl`, completed 18:45:05 UTC | 176 frames, four sections at encoded 10/20/25/50 fps; seven windows; owner: all four work and look progressively faster | These encoded settings render qualitatively; exact physical fps unmeasured | Logged + owner observation |
| Eyes capacity | `captures/eyes-528f-20fps-20261114.jsonl`, completed 18:52:10 UTC | 528 frames at encoded 20 fps, 244,687 bytes, twenty windows; owner confirmed counter reached 528 and looped correctly after disconnect | At least this frame count / file size works; capacity ceiling unknown | Logged + visually confirmed |

## Information exchange and grid verification

`examples/device_info.py` explicitly sends the source-documented time-bearing
query `08 00 01 80 HH MM SS 00`, using `ZoneInfo("Europe/Berlin")`. The actual query
was `08 00 01 80 12 21 2a 00` (18:33:42 CET), with reply
`0b 00 01 80 83 21 2a 00 00 01 00`. The `0x83` type is consistent with the ACT1025
reference, but the panel's printed model is still `3226274 | 37/2026`.
Fields other than length/opcode/type are preserved without invented meanings.

The separate query `04 00 05 80` returned `08 00 05 80 0e 02 07 04`.
The strict parser checks the declared length and opcode; unknown type codes yield
no dimensions, rather than silently falling back to a guessed size.

`examples/corner_test.py --width 64 --height 16` used the verified pixel operation
at `(0,0)`, `(63,0)`, `(0,15)`, `(63,15)` plus two inward-adjacent pixels per corner.
The owner confirmed red top-left, green top-right, blue bottom-left and yellow
bottom-right, all at the expected edges. No persistent orientation-setting
command was used.

## Static live RGB frame experiment

The exact source format in mx2rel's `matrix.js` is implemented only for the now
verified **64×16** dimensions. Other sizes are rejected rather than inferring how
to change undocumented header fields.

```text
09 0c 00 00 00 00 0c 00 00  +  3072 bytes of row-major RGB888
```

Total message length is 3081 bytes. The fixed header is reference-derived; no
individual header-field semantics or checksum is inferred. Pillow renders the
diagnostic preview, and transparency is composited onto black before encoding.
The preview is `captures/static-diagnostic-64x16-20261114.png`.

The negotiated MTU was 517. The experiment conservatively selected
`min(244, MTU-3)` bytes per GATT write, with response enabled and a nominal 10ms
pause after each completion. The application message was split into twelve
244-byte chunks and one 153-byte chunk. There is no background queue or retry
after a partially failed frame. Logs reconstruct exactly the original 3081 bytes.
The observed write interval was approximately 1.8 seconds for this single frame;
it does not establish a sustainable animation frame rate.

FA03 emitted `05 00 00 00 01` after the last write. This is an observed response,
not yet a general-purpose ACK/error specification. Pixel commands had emitted no
notifications; application completion semantics may differ by operation.
The owner reported **no diagnostic image**, with the default `> LED <` startup
artwork shown instead. This attempt is a negative result; `05 00 00 00 01` must
not be treated as successful image rendering. The reason is unverified. Keep
raw mode explicitly experimental; do not enable it as the default image path.

## Confirmed PNG/CRC static-image path

The successful path follows the pinned `pypixelcolor` implementation:

```text
[total length: LE16] 02 00 00 [PNG length: LE32] [CRC32(PNG): LE32] 00 00 [PNG]
```

The last zero is slot 0, described by that reference as non-saving. No persistent
slots or text encoders are implemented; the PNG encoder remains single-window.
Later GIF encoders and multi-window tests are documented in
[GIF_TESTS.md](GIF_TESTS.md) and [EYES_BENCHMARK.md](EYES_BENCHMARK.md). Valid generated
RGB PNGs must fit one 12-KiB source window. This differs from A's legacy `00 65`
trailer, which has not been tested on this unit. No fields were invented to adapt
one format to another.

The diagnostic's optimized RGB PNG is 506 bytes; its framed upload is 521 bytes,
fragmented into 244 + 244 + 33 bytes. Its RGB SHA-256 matches the raw attempt,
so the visual pattern is unchanged. PNG mode performs the documented and already
observed information/version exchange, then sends one CRC-framed image. The reply
is matched by opcode and compared with A's published `05 00 02 00 03`, but visual
confirmation is required independently. Initial PNG attempts failed at connection,
before any image or information bytes were sent; their transport failures do not
establish a protocol mismatch. A further attempt after owner power cycling also
failed before writes. The successful attempt used cached FA-service enumeration.

Successful payload prefix:

```text
09 02 02 00 00 fa 01 00 00 05 42 58 b3 00 00 89 50 4e 47 ...
```

Here `09 02` is the 521-byte framed length, `fa 01 00 00` the 506-byte PNG size,
and `05 42 58 b3` its little-endian CRC32. The three chunks (244, 244, 33 bytes)
reconstruct exactly the logged frame and the saved PNG. The information query and
version query each received their expected response. FA03 then replied
`05 00 02 00 03` following the final PNG chunk. The owner answered **Yes, all
correct** when asked about the full border, corner colors, `64x16` text and RGB bars.
Thus static image rendering is confirmed independently of the reply. The session
disconnected at **17:50:22 UTC / 18:50:22 CET**.

The single PNG's first-to-last GATT write interval was about 150 ms, with the reply
arriving about 179 ms after the first write attempt. This is one small compressed
frame in an established session; it is not a sustainable animation benchmark.
Persistence across power cycles and the full meaning of every response byte
remain untested.

## Windows connection observation

Fresh/default service enumeration repeatedly returned unreachable. A target-only
diagnostic observed one fresh connectable advertisement at -100 dBm, Windows
access status allowed and an unpaired device. Enumerating the known FA service
with cached metadata then connected, with MTU 517 and the same FA02/FA03 layout.
No application bytes were written by that diagnostic.

The following PNG attempt also connected with cached FA-service metadata and
completed its commands. This supports an explicit host-specific workaround, not
a proof that caching alone caused every prior failure; RF quality was variable.
`examples/static_image.py --windows-cached-services` selects this option only for
the supervised experiment. It must be used after verifying the target's GATT
layout. Default scan/inspect behavior remains unchanged. No adapter reset,
pairing, unpairing, authentication change or driver setting was performed.

Later range follow-up: three fresh attempts at the owner's approximately
two-metre desk position on a separate USB supply completed **zero** uploads,
despite the cached-service option. One scan missed the target; two observed
-101 dBm and timed out during connection/setup. No application commands were sent
in any attempt, so these are link/setup failures, not PNG-encoding failures.
Position and power source changed together; neither is isolated as the cause.
See `RANGE_TESTS.md` for raw-capture references and timings. The earlier cache
workaround is therefore not sufficient to establish reliable range.

Subsequent antenna retest: the owner reported installing the PC antennas and
requested another test at the same reported two-metre desk placement and separate
USB supply. ANT1/ANT2/ANT3 all connected and uploaded, with the expected
`0500020003` reply and no retries. Scan RSSI was -67/-69/-74 dBm; PNG writes took
89.6/119.6/119.6 ms. The owner visually confirmed the final ANT3 label and complete
pattern. This strongly implicates reception in the earlier failures and verifies
PNG operation at that placement during these three trials. Cached metadata was
enabled throughout, so fresh enumeration after the antenna change, sustained
reliability and maximum range are still untested. Details and captures are in
[RANGE_TESTS.md](RANGE_TESTS.md).

## Confirmed pixel operation (limited experiment)

`examples/pixel_test.py` reproduced the published pixel operation after the
panel's GATT interface was verified. The repeat finished at **18:24:21 CET** and
disconnected cleanly. The owner confirmed the visible color changes. Source-byte
interpretations are still distinguished from tested behavior:

| Bytes | Observed value | Meaning/evidence |
| --- | --- | --- |
| 0–1 | `0a 00` | Fixed in every successful test; little-endian packet length according to references, not independently varied |
| 2–4 | `05 01 00` | Fixed published pixel-operation prefix; individual field meanings not independently varied |
| 5–7 | `ff 00 00`, `00 ff 00`, `00 00 ff` | RGB ordering visually confirmed by red/green/blue sequence |
| 8–9 | `00 00` in first test | First test used (0,0); later four-corner test verified x/y endpoints and orientation for 64×16 |

Exact successful payloads, written to FA02 with `response=True`:

```text
red:   0a 00 05 01 00 ff 00 00 00 00
green: 0a 00 05 01 00 00 ff 00 00 00
blue:  0a 00 05 01 00 00 00 ff 00 00
```

FA03 notifications were enabled for observation, with none received in either
experiment. Write completion is a GATT transport result, not an application ACK.
The visible effect is established separately by the owner. No handshake,
device-information/time query, display-mode command, full-frame upload or
persistent-slot operation was needed in that first tested state. Behavior in other
states, and whether a pixel survives power cycling, is untested. That first
experiment ended on blue; later grid and image experiments superseded its display.

Discovery observation: private `captures/scan-ready-20261114.json` records an
`LED_BLE_*` candidate with no advertised service UUIDs and RSSI -98 dBm. It is
absent in `captures/scan-off-20261114.json` after the owner unplugged the panel.
One unnamed device also disappeared. `captures/scan-return-20261114.json` records
the same named candidate returning after owner-confirmed power-on. The diagnostic
in `captures/connection-diagnostic-20261114.json` confirms connectable/scannable
advertisements, public address type and RSSI -96 dBm. Specifying that address type
did not resolve sandbox connection failure. Host inspection then failed with
GATT services unreachable. After power was moved to the PC,
`captures/scan-pc-usb-20261114.json` recorded the same target at -86 dBm and
the subsequent host GATT inspection succeeded. Multiple conditions changed;
neither antenna quality nor distance nor the supply is established as the cause.
No application packet semantics are confirmed by these observations.

Gate for first pixel: identify our panel by off/on comparison and save its GATT
metadata. A controlled official-app capture is preferred. Alternatively, after a
GATT match, reproduce a bounded, published reference pixel operation whose byte
format agrees across inspected implementations. Treat it as an experiment until
visually confirmed; do not infer initialization or send unrelated commands.
The owner has an iPhone and has not installed iPixel Color, so we are taking the
published-operation route for one pixel, not building a speculative full driver.
`examples/pixel_test.py` limits this to three writes at (0, 0), red/green/blue,
captures FA03 notifications, and sends no handshake or information/time exchange.
The later device-info/corner experiments established grid size/orientation and
the PNG/CRC experiment verified one full static image. Raw RGB failed its visual
test. Subsequent sprite passes verified host PNG streaming at 2 fps and 5 fps
for ten seconds each, the latter with visible frame counters; see
[ANIMATION_TESTS.md](ANIMATION_TESTS.md). Permanent-slot operations,
host-streaming rates above 5 fps and runs beyond one minute remain unverified. A later one-minute
5 fps check delivered 300/300 acknowledged frames, all reported visible, with
possible uneven pacing. Exact screen timing and uniformly paced rendering remain
unverified; see the animation results for measured upload and reply intervals.

## Confirmed panel-local GIF experiment

The pinned `pypixelcolor` builder uses
`[length LE16] 03 00 00 [GIF length LE32] [CRC32 LE32] 02 00 [GIF]`
for a single-window GIF in slot 0. The generated twenty-frame 64×16 GIF has
200 ms encoded frame durations and an infinite-loop extension. One 4103-byte
message in 17 acknowledged GATT chunks elicited `05 00 03 00 03`. Its exact
prefix was `07 10 03 00 00 f8 0f 00 00 ab ce 4c 42 02 00`.

The session then disconnected and sent no application writes during a twelve-
second observation period. The owner confirmed the counter continued looping
with steady-looking timing. This establishes local playback of this GIF after
disconnect, independently of its reply. Exact physical frame timing, power-cycle
persistence, persistent slots and maximum GIF size/frame count remain unverified.
See [GIF_TESTS.md](GIF_TESTS.md) for source links, timestamps and captured evidence.

Multi-window follow-up: the pinned builder repeats full GIF size and CRC in
every 12-KiB window, changes option byte from 00 to 02 after the first window,
and prefixes each window with that window's message length. A 44-frame eyes GIF
uploaded in two windows and rendered correctly, confirmed by the owner. Status 1
was observed for the intermediate window and status 3 for the final window.
A subsequent 176-frame rate-comparison file uploaded in seven windows with the
same intermediate/final status pattern; the owner confirmed all four encoded
10/20/25/50 fps settings worked and looked progressively faster. A 528-frame
244,687-byte file at encoded 20 fps then uploaded in twenty windows, with nineteen
status-1 replies and final status 3. After disconnect, the owner confirmed its
counter reached 528 and restarted at 001. The exact physical playback rate and
hardware frame-count/file-size ceiling remain unknown; the tool's 256-KiB /
600-frame bounds are deliberately limited experiments, not measured specifications.
See [EYES_BENCHMARK.md](EYES_BENCHMARK.md) for limits, source art and current status.

## Later direct library transport probes

The actual pinned `pypixelcolor` builders, ACK manager and send loop have now been
exercised with our Windows connection/logging adapter. The public Client lifecycle
is still untested. Fast unacknowledged GIF uploads returned final status 3 but
visibly froze at frames 002 and 006 in separate attempts; acknowledged writes
recovered playback. A final application ACK therefore does not guarantee a
correctly playing GIF. A small twenty-frame GIF rendered correctly using
500-byte acknowledged chunks. The device advertised MTU 517 and a 514-byte
write-without-response maximum during these probes.

Full PNG updates failed to sustain the latest 10/20 fps schedules. Coordinate-only
motion completed its host submission schedules, but the owner reported only
yellow pixels resembling corruption. Do not infer rendered frame rate, PNG
overlay preservation or a native rectangle update from those timings. The
earlier isolated corner writes remain visually verified. See
[LIBRARY_PANEL_TESTS.md](LIBRARY_PANEL_TESTS.md) for exact counts and qualifications.

The subsequent 1,024-frame (479,139-byte) and 2,048-frame (958,185-byte) GIFs both
received owner confirmation of complete playback and looping after disconnect.
The largest encoded loop is 102.4 seconds at 20 fps. Its actual library plan used
78 application windows and 1,950 acknowledged 500-byte-or-smaller GATT writes,
with 77 intermediate status-1 replies and final status 3. Upload took 105.544 s.
The first 2,048-frame attempt was deliberately interrupted; only its fresh,
complete retry counts. These are slot-0 playback capacity lower bounds, not
persistent-storage capacity measurements or a hardware maximum.

A separate 4,088-byte original twenty-frame GIF was saved to slot 1 with the
same builder, changing only header byte 14 from 0 to 1. Nine acknowledged writes
returned final status 3 in 0.364 s. The owner confirmed normal playback, removed
power for five seconds, restored power and observed the boot animation followed
automatically by our saved GIF, before any new PC connection. This confirms
retention and startup playback for this fixture after one power cycle. Persistent
capacity and other slot-selection semantics remain unmeasured.

A subsequent 4,096-frame, 1,915,364-byte slot-0 GIF uploaded in 216.759 s over
156 windows and 3,897 acknowledged GATT writes. All 155 intermediate status-1
replies and final status 3 matched expectations, and captured chunks matched
the upstream builder exactly. After disconnected observation the owner confirmed
all 4,096 frames shown correctly. The encoded loop is 204.8 seconds at 20 fps;
exact display timing and the hardware capacity ceiling remain unmeasured.

Further image/partial-update probes isolated these behaviors:

- A four-bit indexed PNG returned final status 3 but displayed black. The compact
  RGB replacement with a 3-by-5 bitmap HUD rendered correctly. All 100 numbered
  RGB frames at scheduled 10 fps were acknowledged and visually confirmed; the
  15/20 fps probes stopped at software scheduling cutoffs, not a proven panel FPS
  ceiling. Fast PNG transport did not establish stable 15 fps either.
- In one uninterrupted connection, adding a green block preserved red, and
  black coordinate writes removed red while green remained. The owner observed
  individual pixel updates. This verifies slow partial coordinate editing of
  pixel-drawn content, not an atomic rectangle update.
- A same-connection PNG-then-pixel patch showed only the new red block: PNG
  overlay preservation failed. A separate-connection comparison was invalidated
  by the owner's observation that connection setup changes the display.
- The corrected same-connection fast native-pixel animation included a counter
  and preserved static pixels in software, but visibly corrupted on hardware.
  It reached 47 submitted frames before the script's scheduling cutoff. Its
  final info query took 1.654 s, including notification changes; this is not a
  measured display delay.
