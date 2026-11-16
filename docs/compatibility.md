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

One setup has been tested. Batch labels and version byte pairs are not interpreted
as product-wide firmware guarantees. Unknown device types are rejected rather
than assumed to be 64x16.

## Verified operations

- PNG uploads with upstream framing and CRC, including complete game frames.
- GIF uploads that continue looping after the PC disconnects.
- A 1,915,364-byte, 4,096-frame numbered GIF, visually confirmed by the owner.
  This is a successful file, not a measured maximum capacity.
- A small GIF saved in slot 1 resumed after an owner-performed power cycle.
  Persistent capacity beyond that sample remains unmeasured.
- Single-pixel updates and static same-colour grouped pixels on the separately
  tested upstream PR #88 branch.
- Snake, Starfall and Micromaze gameplay; Windows 12-fps Starfall play and reconnect.

## Limits and negative findings

- The raw RGB888 reference did not render the diagnostic image on this panel.
- Fast small-PNG uploads worked, but did not establish a throughput advantage
  over acknowledged writes. Fast GIF and native-pixel failures remain unresolved.
- Concatenated pixel commands and two-image PNG pipelining did not establish a
  reliable supported path. They are not enabled in the application.
- The apparent Snake tail gap was also seen with PNGs; it was not isolated to
  the grouped-pixel feature. Generated source images had continuous tails.
- Indexed PNGs returned a completion reply but displayed black in the tested
  experiment. The app uses RGB PNGs.
- Completion replies measure accepted uploads, not instrumented physical LED
  refresh, visible smoothness or keyboard-to-display latency.

See [validation](validation.md) for measurements and the underlying reports.
Downloaded third-party artwork stays in private test archives; it is not shipped
with the games. Provenance is retained in [the art report](archive/ART_SOURCES.md).
