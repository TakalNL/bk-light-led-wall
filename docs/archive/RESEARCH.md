# Reference implementation research

Reviewed 2026-11-14. All five requested repositories exist and were inspected
locally at the commits below, including README, transport/encoding source and
available protocol documents. Reference code was not executed against hardware
or copied into our package. Local reference checkouts are ignored in `.research/`.

**Recommendation:** start with the FA-family used by references A/B. A is the
strongest of the five requested references because its brand, retailer and Python
transport match. The owner's additional **iPixel Color** app identification makes
the supplemental `pypixelcolor` library especially promising for eventual reuse.
Neither reference establishes support for article **3226274**, label **37/2026**,
or the advertised **16×51** layout. First collect our own advertisements and GATT.

## Evidence categories

- **Confirmed in source:** directly present in the inspected implementation;
  this does not mean confirmed on our panel.
- **Plausible similarity:** matching brand, app, UUID or packet pattern.
- **Unverified:** requires our unit, a capture or a controlled experiment.
- **Known mismatch:** source formats/target hardware differ; applying one family's
  packets directly to another is unjustified. Our unit's family is still unknown.

## Comparison

Full UUIDs below use the Bluetooth base `0000XXXX-0000-1000-8000-00805f9b34fb`,
except service `00FA`, whose full spelling is `000000fa-0000-1000-8000-00805f9b34fb`.

| Reference | Documented hardware | Source-confirmed transport/encoding | License check | Compatibility assessment |
| --- | --- | --- | --- | --- |
| [A: Bk-Light-AppBypass](https://github.com/Pupariaa/Bk-Light-AppBypass) | Action B.K. Light ACT1025 64×16 and ACT1026 32×32 | Python/Bleak, FA02 writes, FA03 notifications; PNG upload with little-endian lengths, CRC32 and handshake/ACK sequence | MIT LICENSE present; retain notice if copying | Highest-priority requested reference; 51×16 unverified |
| [B: BK-Light-LED-rx-engine](https://github.com/mx2rel/BK-Light-LED-rx-engine) | Action B.K. Light LED Fun Screen 64×16 | Web Bluetooth, service 00FA / FA02; individual pixels and row-major RGB888 full frames | README claims MIT, but no LICENSE file in inspected tree; clarify grant/notice before copying | Same FA02 and related command framing as A; exact controller identity and our compatibility unverified |
| [C: coolledx-driver](https://github.com/UpDryTwist/coolledx-driver) | CoolLEDX / CoolLED1248-app signs, variable dimensions | Python/Bleak, FFF1; escaped 01…03 framing, 128-byte content chunks and XOR checksum; RGB bitplanes | MIT LICENSE present | Different candidate family; newer device names do not prove implemented support |
| [D: coolledux-ble](https://github.com/CharlesLennon/coolledux-ble) | CoolLEDUX, author tested one 64×16 unit | Python/Bleak FFF0 / FFF1; escaped envelope, custom CRC32, LZSS program uploads, RGB444 content | MIT LICENSE present | Advanced CoolLED family; not interchangeable with C's simple protocol or FA-family |
| [E: mi-led-display](https://github.com/offe/mi-led-display) | Merkury Innovations MI-LNL62-999W, 16×16 in scripts | Python/Bleak FFD0 / FFD1; BC…55 packets, RGB pixel/block updates | MIT LICENSE present | Different hardware and packet family; capture methodology is reusable |

## A — Python B.K. Light reference

Snapshot: [`f83b90e9a8229d3c3bfca9568733c1f15afc795c`](https://github.com/Pupariaa/Bk-Light-AppBypass/tree/f83b90e9a8229d3c3bfca9568733c1f15afc795c).
Latest commit in checkout: **2026-04-04**, merging native scrolling work.
The README requires Python 3.13; our independent discovery tools target 3.11+.

The [session implementation](https://github.com/Pupariaa/Bk-Light-AppBypass/blob/f83b90e9a8229d3c3bfca9568733c1f15afc795c/bk_light/display_session.py)
scans by address, connects with Bleak and subscribes to FA03. Image transmission
starts with two FA02 handshake writes and waits for recognized response variants
for the two ACT models. PNG bytes receive a 15-byte header including length fields
and standard CRC32. Frame writes request a GATT response, then wait separately for
an application ACK. Validation is sent every 30 frames. ACK waits are five seconds;
bounded retry/reconnection logic repeats setup after failures.

Image rotation and brightness in this path are Pillow transformations before PNG
encoding, **not evidence of a hardware brightness command**. Images use RGB PNGs;
that does not reveal physical wiring or LED channel order. The session passes the
whole frame to a GATT write rather than explicitly fragmenting it; long-write/MTU
support must be verified, and its attempted `exchange_mtu` failure is suppressed.
Do not copy that transport assumption to a new controller.

[Panel management](https://github.com/Pupariaa/Bk-Light-AppBypass/blob/f83b90e9a8229d3c3bfca9568733c1f15afc795c/bk_light/panel_manager.py)
slices a virtual canvas across independent connections and uses asynchronous
dispatch. This is host coordination, not proof of manufacturer dual-panel pairing
or synchronized refresh. Discovery scripts filter names such as `LED_BLE_*`;
our discovery intentionally remains unfiltered.

The [native-scroll document](https://github.com/Pupariaa/Bk-Light-AppBypass/blob/f83b90e9a8229d3c3bfca9568733c1f15afc795c/NATIVE_TEXT_SCROLL_PROTOCOL.md)
adds a hardware-validated ACT1025 text route, not evidence about our 2026 unit.
Reusable ideas: separate sessions/rendering, explicit ACK events, bounded retries
and per-panel cropping. No verified maximum animation rate or 51-column support.

## B — Web Bluetooth B.K. Light reference

Snapshot: [`a5a1bfd201081a4ddf2ed012f11c36eb7e40e9d8`](https://github.com/mx2rel/BK-Light-LED-rx-engine/tree/a5a1bfd201081a4ddf2ed012f11c36eb7e40e9d8).
Latest checkout commit: **2025-11-23**, README update. Small hobby implementation;
no ongoing support guarantee inferred.

[matrix.js](https://github.com/mx2rel/BK-Light-LED-rx-engine/blob/a5a1bfd201081a4ddf2ed012f11c36eb7e40e9d8/matrix.js)
uses 00FA / FA02. Its pixel operation builds a ten-byte command containing RGB and
x/y. Full frames use a fixed nine-byte header plus 3,072 row-major RGB bytes for
64×16. It writes chunks of **500 bytes**, with ten milliseconds between them.
The nearby 244-byte comment disagrees with the actual constant; neither is a
universally safe BLE payload size. Frame submission is throttled at 200 ms with
an in-progress guard. There is no FA03 ACK handling or automatic reconnect loop.
The initialization bytes are defined, but the actual write is commented out.

The [README](https://github.com/mx2rel/BK-Light-LED-rx-engine/blob/a5a1bfd201081a4ddf2ed012f11c36eb7e40e9d8/readme.md)
reports roughly 5 FPS, occasional lag and accumulating delay during continuous
transmission. Its internal buffering explanation is the author's hypothesis,
not a confirmed controller mechanism. Examples include Snake, clock and drawing;
a Spotify widget is linked on a separate branch, not audited here.

A/B share FA02, little-endian length-style framing and overlapping command
patterns. They plausibly expose different operations in one broader iPixel
family: encoded PNG upload versus direct pixel/raw framebuffer. **The sources do
not establish identical controller chipsets**, and differing data paths do not
prove different families. Reuse the pacing/backpressure lessons and pixel-capture
comparison; do not resize the fixed 64×16 packet by guesswork.

## C — CoolLEDX Python reference

Snapshot: [`ba24137a4fb63b44896143adbd5862ef74de9fff`](https://github.com/UpDryTwist/coolledx-driver/tree/ba24137a4fb63b44896143adbd5862ef74de9fff).
Latest checkout commit: **2026-01-01** (author offset −05:00). Contains tests,
packaging and connection troubleshooting docs; these are not proof every variant
works. README explicitly warns about unsupported CoolLEDM devices.

[client.py](https://github.com/UpDryTwist/coolledx-driver/blob/ba24137a4fb63b44896143adbd5862ef74de9fff/src/coolledx/client.py)
uses FFF1 for writes/notifications, scans by name/address and parses dimensions
from manufacturer data under its own layout assumptions. Its ACK interpretation
is explicitly approximate. [commands.py](https://github.com/UpDryTwist/coolledx-driver/blob/ba24137a4fb63b44896143adbd5862ef74de9fff/src/coolledx/commands.py)
constructs indexed 128-byte content chunks with lengths and XOR checksum. The
simple envelope has a big-endian length and escapes bytes 01–03.
[render.py](https://github.com/UpDryTwist/coolledx-driver/blob/ba24137a4fb63b44896143adbd5862ef74de9fff/src/coolledx/render.py)
builds separate column-oriented RGB bitplanes, thresholding each channel, including
image/animation content. It is not A/B's raw RGB888 or PNG path.

The inspected HEAD appears incomplete: `Command.get_command_chunks()` calls
`self.create_command`, but `Command` does not inherit the separate `BasicProtocol`
that defines it; `AdvancedProtocol` is an empty class. Hardware classes and
message-handler placeholders for CoolLEDUX do not demonstrate a working advanced
implementation. This is a source finding, not a runtime/hardware test.

Reusable ideas: protocol separation, recorded fixtures, connection timeout
documentation and [HCI analysis utilities](https://github.com/UpDryTwist/coolledx-driver/blob/ba24137a4fb63b44896143adbd5862ef74de9fff/utils/bt_analyzer.py).
Those utilities use PyShark/TShark with family-specific filters; don't apply their
fixed handles/UUID interpretation to ours.

## D — Advanced CoolLEDUX reference

Snapshot: [`4f5656d9882adb4926c9dff4dc3fa5783b40a7ac`](https://github.com/CharlesLennon/coolledux-ble/tree/4f5656d9882adb4926c9dff4dc3fa5783b40a7ac).
Latest checkout commit: **2026-07-26**, example link. Small initial history;
author reports validation on one 64×16 sign, with firmware variation unresolved.

[wire.py](https://github.com/CharlesLennon/coolledux-ble/blob/4f5656d9882adb4926c9dff4dc3fa5783b40a7ac/coolledux/wire.py)
implements escaped 01…03 packets, a non-reflected CRC32 without final complement,
and LZSS-compressed program uploads. These CRC semantics differ from A's standard
PNG CRC32. [colors.py](https://github.com/CharlesLennon/coolledux-ble/blob/4f5656d9882adb4926c9dff4dc3fa5783b40a7ac/coolledux/colors.py)
uses RGB444 with content-dependent transfer curves and documented background
sentinels. Source comments about dropped-byte behavior are author interpretations,
not independently verified transport guarantees.

The [transport](https://github.com/CharlesLennon/coolledux-ble/blob/4f5656d9882adb4926c9dff4dc3fa5783b40a7ac/coolledux/ble.py)
uses FFF0 / FFF1, writes without response and defaults to 60 ms chunk pacing.
Notifications for direct commands are not reliable content-chunk ACKs. Its
[protocol reference](https://github.com/CharlesLennon/coolledux-ble/blob/4f5656d9882adb4926c9dff4dc3fa5783b40a7ac/PROTOCOL.md)
distinguishes tested, source-only and unimplemented features. Stored animations
and native GIF playback differ from streaming frames; full-width animation uses
tiled segments to work around an author-observed width constraint.

Reusable ideas: pure content/wire builders, confidence labels and explicit
separation of program upload from live commands. Shared FFF1 with C is insufficient
to choose the simple versus advanced protocol. iPixel Color currently makes this
a lower-priority reference for our unit.

## E — Merkury reference and capture workflow

Snapshot: [`97a1be8b4edefc7eccdd2f3943997b4416d44771`](https://github.com/offe/mi-led-display/tree/97a1be8b4edefc7eccdd2f3943997b4416d44771).
Latest checkout commit: **2025-03-12**. Experimental scripts and captures rather
than a maintained cross-model library.

[draw_pixels.py](https://github.com/offe/mi-led-display/blob/97a1be8b4edefc7eccdd2f3943997b4416d44771/draw_pixels.py)
selects `MI Matrix Display`, uses FFD0 / FFD1, initialization commands and BC…55
pixel updates. [draw_picture.py](https://github.com/offe/mi-led-display/blob/97a1be8b4edefc7eccdd2f3943997b4416d44771/draw_picture.py)
sends eight 32-pixel RGB blocks for 16×16. Its docstring says 113 bytes, but the
code builds **100 bytes** (3 header + 96 data + terminator). Pixel index/check
descriptions also disagree between comments and protocol notes. Prefer captures
over trusting those explanations. Dimensions/framing are a known mismatch with
the candidate FA-family; our unit has not been tested for either.

The useful [snoop instructions and exported captures](https://github.com/offe/mi-led-display/tree/97a1be8b4edefc7eccdd2f3943997b4416d44771/snoops)
describe Android logging, bugreports, Wireshark ATT filtering and including packet
bytes in exports. README links `snoop_instructions.md`, which is absent in the
inspected tree; the actual instructions are `snoops/README.md`. Capture techniques
are reusable even when packet semantics are not.

## Supplemental lead from the owner's app identification

[`lucagoc/pypixelcolor`](https://github.com/lucagoc/pypixelcolor/tree/c8cbaebca6df7797a7bcface8a1c4ca33e499973),
commit **c8cbaebca6df7797a7bcface8a1c4ca33e499973**, latest checkout commit
**2026-11-12**. Reviewed README, MIT LICENSE.md, transport constants, session,
device-info parser, pixel/image builders and Android capture guide. This library
explicitly targets iPixel Color and has recent development, making it a strong
candidate to adapt after first contact rather than building another full driver.

[Constants](https://github.com/lucagoc/pypixelcolor/blob/c8cbaebca6df7797a7bcface8a1c4ca33e499973/src/pypixelcolor/lib/constants.py)
match FA02/FA03. Its [pixel builder](https://github.com/lucagoc/pypixelcolor/blob/c8cbaebca6df7797a7bcface8a1c4ca33e499973/src/pypixelcolor/commands/set_fun_mode.py)
matches B's ten-byte RGB/x/y operation. Image sending has CRC32, PNG/GIF paths and
windowed upload plans. This strengthens the broader-family interpretation of A/B.

However, [connect setup](https://github.com/lucagoc/pypixelcolor/blob/c8cbaebca6df7797a7bcface8a1c4ca33e499973/src/pypixelcolor/lib/device_session.py)
automatically subscribes and sends device-information commands, including a
time-bearing exchange. It is unsuitable for our initial read-only inspection.
The [dimension parser](https://github.com/lucagoc/pypixelcolor/blob/c8cbaebca6df7797a7bcface8a1c4ca33e499973/src/pypixelcolor/lib/device_info.py)
uses a device-type lookup table with **no 51×16 entry** and a 64×64 fallback for
unknown types. Do not treat that fallback as a measurement. No source reviewed
here confirms the owner's exact model/layout.

## Decision and remaining evidence

Proceed with unfiltered scan, off/on identification and metadata-only inspection.
If the selected panel exposes the FA-family characteristics, compare a controlled
iPixel Color capture before replaying a pixel operation. If it exposes FFF1 or
FFD1, revise the family hypothesis using observed framing; do not send commands
from all five drivers in sequence.

Hardware follow-up on 2026-11-14: owner-operated on/off/on scans identified the
panel, and metadata-only GATT inspection succeeded. The actual services include
00FA with FA02 write/write-without-response and FA03 notify, plus AE00. Thus the
FA-family interface match is now observed, strengthening A/B and `pypixelcolor`
as references. This does not confirm their pixel commands or dimension mapping.
See `PROTOCOL.md` and the private `captures/gatt-pc-usb-20261114.json`.

Pixel follow-up on the same date: a bounded test reproduced the matching pixel
command from B and `pypixelcolor`, with no handshake or information query. The owner
confirmed a corner pixel changing red/green/blue during the repeat. Thus the
single-pixel operation at (0,0) now has hardware evidence. No full driver was built.
The owner uses an iPhone and has not installed iPixel Color.

The current [Action listing for article 3226274](https://www.action.com/nl-nl/p/3226274/briloner-led-berichtenbord/)
calls the product Briloner and specifies physical dimensions **96×369×13 mm**.
It does not establish a pixel resolution. The owner's B.K. Light label is retained
as direct evidence; neither this listing nor the references verify the brief's
16×51 pixel count.

Further hardware follow-up: type `0x83` and the owner's physical four-corner check
established **64×16**, top-left origin, x right and y down. Version replies contain
`[14,2]` and `[7,4]`; chipset identity remains unknown. B's fixed raw RGB frame
was transmitted with GATT responses, but the owner saw default startup artwork,
not the diagnostic image. This is a negative compatibility result for that tested
path, not proof of a different chipset or universal incompatibility.
`pypixelcolor`'s PNG/CRC frame in slot 0 **then worked**: the panel returned
`05 00 02 00 03` and the owner confirmed the complete diagnostic pattern. A uses
a different `00 65` trailer, not yet tested. This makes the `pypixelcolor` framing
the strongest currently validated image reference for this particular unit.
Connection failures before writes were recorded separately from protocol outcomes;
the successful PNG attempt opted into Windows' cached metadata for the known FA
service after a read-only diagnostic showed that path could connect.

Animation follow-up: repeated PNG host streaming worked at 2 fps and 5 fps;
the one-minute 5 fps run delivered all 300 frames with possible uneven pacing.
Then the pinned `_build_send_plan` GIF branch was inspected directly: opcode
`03`, marker `02`, CRC32 and slot 0. A single-window 4088-byte numbered GIF
elicited `0500030003`, and the owner confirmed it kept looping with steady-looking
timing after the host disconnected. This verifies the small GIF local-playback
path on our unit; see [GIF_TESTS.md](GIF_TESTS.md). GIF timing is encoded as 200 ms
per frame, not measured from the physical display.

We still need controller identity, persistence and richer commands. Maximum
frame rate, exact display timing and multi-panel synchronization are not established.
The checklist and capture procedure are in [HARDWARE_TESTS.md](HARDWARE_TESTS.md).

Real-art follow-up: inspecting the same pinned GIF `_build_send_plan` established
that continuation windows repeat whole-file size/CRC and set option 02. The
implementation was bounded to 256 KiB, with every window acknowledged before the
next. Hardware tests of two, seven and twenty windows all worked; intermediate
status 1 and final status 3 were observed. Native-size online eyes art rendered
at all four encoded 10/20/25/50 fps settings with owner-reported increasing speed;
the 528-frame test at encoded 20 fps reached 528 and looped after disconnect.
See [EYES_BENCHMARK.md](EYES_BENCHMARK.md) and [ART_SOURCES.md](ART_SOURCES.md).
No hardware capacity ceiling or instrumented physical frame rate is inferred.

Our implementation follows the current primary [Bleak scanner](https://bleak.readthedocs.io/en/latest/api/scanner.html)
and [client](https://bleak.readthedocs.io/en/latest/api/client.html) interfaces.
No third-party protocol code or bundled artwork/fonts were copied. Any later code
reuse must preserve its applicable license/notice; bundled assets need separate review.

Later direct-library work installed the pinned `pypixelcolor` checkout and used
its real builders, ACK manager and send loop through our Windows connection
adapter; the public Client lifecycle remains untested. Owner-confirmed findings
now include 4,096-frame slot-0 playback, power-cycle retention/startup of a tiny
slot-1 GIF, and a short 10 fps compact RGB PNG stream. Same-session coordinate
add/erase preserves other pixel-drawn content, but did not overlay an uploaded
PNG. Fast GIF and native-pixel motion visibly failed. These are hardware
compatibility findings using upstream code, not original protocol inventions.
See [LIBRARY_PANEL_TESTS.md](LIBRARY_PANEL_TESTS.md) for current results, failed
probes, timing definitions and the completed capacity observations.
