# Hardware compatibility

## Tested configuration

| Item | Observed value |
| --- | --- |
| Panel | B.K. Light / Action article 3226274; label includes 37/2026 |
| App reported by owner | iPixel Color |
| Grid | 64x16; top-left origin, x right, y down |
| Device type | `0x83` (131) |
| Raw version reply | `080005800e020704`; version byte pairs [14, 2] and [7, 4] |
| BLE | Service 00FA, FA02 writes, FA03 notifications |
| Host used for hardware checks | Windows, Intel Wireless Bluetooth, CPython 3.13.9, Bleak 3.1.0 |
| Reported MTU | 517 |

One Windows host and two 64×16 panels have been tested. Batch labels and version byte pairs are not interpreted
as product-wide firmware guarantees. Unknown device types are rejected rather
than assumed to be 64x16.

## Verified operations

- PNG uploads with upstream framing and CRC, including complete game frames.
- GIF uploads that continue looping after the PC disconnects.
- Native clock style 1 on the top panel: green time, blinking colon and animated
  character; the owner confirmed minutes advance after Bluetooth disconnects.
  Other styles and retention after loss of power remain untested. See the
  [capability map](panel-capabilities.md).
- A 1,915,364-byte, 4,096-frame numbered GIF, visually confirmed by the owner.
  This is a successful file, not a measured maximum capacity.
- A small GIF saved in slot 1 resumed after an owner-performed power cycle.
  Persistent capacity beyond that sample remains unmeasured.
- Single-pixel updates and static same-colour grouped pixels on the separately
  tested upstream PR #88 branch.
- Six-byte business-remote command `060007800100` triggered a resident scrolling
  sequence on the top panel without uploading media. Its content's origin and
  arbitrary custom-content selection remain unresolved. See the
  [program/region report](archive/PROGRAM_REGIONS_TESTS.md).
- Snake, Starfall and Micromaze gameplay; Windows 12-fps Starfall play and reconnect.
- Two simultaneous verified 64×16 links accepting a shared stacked 64×32 canvas;
  owner confirmed panel 1 is physically above panel 2. See the
  [wall controller](../games/wall/README.md) for layout and playback controls.
- Restarting a previously uploaded native GIF with a 15-byte header. Concurrent
  restarts brought deliberately offset loops on both panels into close visible
  alignment; the owner observed a small, steady bottom-panel lead. Physical
  timing and long-term drift remain unmeasured. See the
  [capability map](panel-capabilities.md).

## Limits and negative findings

- The raw RGB888 reference did not render the diagnostic image on this panel.
  The readable Android APK instead uses JPEG bytes for at least its Pong bitmap
  and CameraX frame paths. One test with that recovered framing elicited a reply
  but showed the default boot image; correct JPEG rendering was not demonstrated.
- Fast small-PNG uploads worked, but did not establish a throughput advantage
  over acknowledged writes. Fast GIF and native-pixel failures remain unresolved.
- Concatenated pixel commands and two-image PNG pipelining did not establish a
  reliable supported path. They are not enabled in the application.
- APK-derived DIY mode 3 followed by grouped painting showed only the new square,
  losing the preceding PNG background. A fully native two-square baseline worked,
  but the tested right-movement and horizontal-mirror packets produced no confirmed
  visible shift or swap. Other parameters and entry states remain unresolved;
  see the [capability map](panel-capabilities.md).
- The apparent Snake tail gap was also seen with PNGs; it was not isolated to
  the grouped-pixel feature. Generated source images had continuous tails.
- Indexed PNGs returned a completion reply but displayed black in the tested
  experiment. The app uses RGB PNGs.
- One candidate native text/image region preview showed the default LED image;
  correct composition was not established. Program-list declaration replied
  but left the BASE diagnostic visible. See the
  [program/region report](archive/PROGRAM_REGIONS_TESTS.md) for entry/codec limits.
- Completion replies measure accepted uploads, not instrumented physical LED
  refresh, visible smoothness or keyboard-to-display latency.
- Combined uploads are coordinated in software. Atomic multi-panel display swaps
  and a shared refresh clock are unverified; larger panel counts are untested.

See [validation](validation.md) for measurements and the underlying reports.
The [capability map](panel-capabilities.md) inventories further app-exposed
functions and separates packet-code evidence from verified panel behavior.
Downloaded third-party artwork stays in private test archives; it is not shipped
with the games. Provenance is retained in [the art report](archive/ART_SOURCES.md).
