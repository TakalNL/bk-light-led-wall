# Local draft: B.K. Light 3226274 protocol compatibility observations

Status: **draft only; not posted**. Intended first destination:
https://github.com/lucagoc/pypixelcolor/discussions (compatibility observations)
or its issue tracker if the maintainer prefers that format. A documentation PR
may be more appropriate once the maintainer identifies a suitable location.

Suggested title: `Hardware observations: Action B.K. Light 3226274, label 37/2026, 64x16`

## Suggested report body

Thank you for publishing pypixelcolor. We used your protocol implementation as
the principal reference while testing a B.K. Light panel from Action.

Qualification: initial tests used our own Python/Bleak implementations of the
formats in your pinned commit `c8cbaebca6df7797a7bcface8a1c4ca33e499973`.
Subsequent tests directly use that checkout's builders, `AckManager` and
`send_plan`, with our instrumented adapter for the verified Windows connection
settings, logging, bounds and optional pacing. No upstream source was changed.
The initial capacity/streaming observations below used the adapter, not the
public client lifecycle. A subsequent unmodified public `AsyncClient` trial on
2026-11-16 passed connection, same-instance reconnect and a second fresh-client
session uploading an original diagnostic PNG and twenty-frame GIF to slot 0.
The owner confirmed both rendered correctly and the GIF looped after disconnect.
No forced cache settings, service filters, chunk overrides or added pacing were
used in that trial. A subsequent two-minute Starfall replay completed 1,175/1,200
scheduled PNG updates via the default public API (9.78 fps), versus 1,200/1,200
through the adapter (10 fps). The owner confirmed both looked correct, with
little visible difference; see [STARFALL_STREAM_TESTS.md](STARFALL_STREAM_TESTS.md).
Larger public-API uploads remain untested. The capacity observations below
remain adapter-based; see [PUBLIC_CLIENT_TESTS.md](PUBLIC_CLIENT_TESTS.md).

The local application has since consolidated its game and instrumented experiment writes
onto this backend, removing its parallel image framing and experimental send
loop. This cleanup does not change the qualifications of the historical tests.

Hardware/context:

- Owner-reported brand: B.K. Light; Action article 3226274.
- Label includes `37/2026`; its meaning is not asserted.
- Owner-reported app: iPixel Color; it was not used for these tests.
- Verified dimensions/orientation: 64×16, origin top-left, x right, y down.
- Information type `0x83`; version reply `080005800e020704`, preserved as raw
  MCU pair `[14, 2]` and secondary pair `[7, 4]` without assigning release names.
- BLE FA service, FA02 write / FA03 notify; AE00 also present but not exercised.
- Tested host: Windows, Intel Wireless Bluetooth, CPython 3.13.9, Bleak 3.1.0.
  GATT-reported MTU 517. Target unique address omitted.

Observed operations:

| Operation | Evidence |
| --- | --- |
| Pixel command | Owner confirmed RGB sequence and four colored corner markers |
| PNG CRC upload, slot 0 | Complete diagnostic image confirmed; reply `0500020003` |
| GIF CRC upload, slot 0 | Numbered animation continued looping after BLE disconnect; reply `0500030003` |
| Continuation windows | Up to 156-window GIF uploads worked; status 1 for intermediate windows, status 3 for final window |
| Larger GIF | 1,915,364 bytes, 4,096 numbered frames at encoded 20 fps; owner confirmed all frames shown correctly after disconnect; encoded loop 204.8 seconds |
| Encoded GIF rates | 10/20/25/50 fps sections all rendered and looked progressively faster to the owner; physical refresh was not instrumented |
| Slot 1 retention | Our original 4,088-byte twenty-frame GIF resumed automatically after boot animation following an owner-performed power cycle, before any new PC connection |
| Compact RGB live frames | 100/100 numbered full PNGs at scheduled 10 fps, owner-confirmed intact motion/background; 15/20 fps probes hit our scheduling cutoff |
| Coordinate drawing | Within one uninterrupted connection, adding a green block preserved red; black writes erased only red, leaving green; visually sequential, not an atomic rectangle operation |
| PNG/pixel interaction | Pixel drawing replaced the PNG view in a same-connection static probe; it did not preserve the PNG as an overlay background |

Initial transport used sequential acknowledged chunks up to `min(244, MTU-3)`
bytes, nominal 10 ms sleeps after completion, one pending application reply and
no partial-message retries. The newer actual-library capacity tests used
500-byte acknowledged chunks with the same pacing. The 4,096-frame file required
156 windows and 3,897 GATT writes; upload took 216.759 seconds. The recorded
chunks exactly matched the actual upstream builder's plan. MTU was 517 and the
advertised maximum write-without-response size was 514 bytes.

Fast GIF transport remains unverified on this unit. Two 20,500-byte GIF trials with
244-byte unacknowledged writes returned final status 3 but visibly froze at
frames 002 and 006. The first used no extra pacing; the second used 10 ms pacing
and a one-second connected settle. Acknowledged uploads restored normal playback.
A same-connection fast native-pixel animation also visibly corrupted. Host write
completion and final image replies are insufficient proof of correct rendering;
these observations do not establish the cause or a library/firmware defect.

A later public-client fast-mode small-PNG trial did pass a fully watched
two-minute 10-fps run with all 1,200 uploads completed and correct rendering.
At requested 15 fps, fast and acknowledged writes averaged 11.188 and 10.863 fps,
with occasional brief pauses/missing frames reported in both. This does not
establish a meaningful speed advantage or resolve the GIF/pixel failures; see
[FAST_MODE_TESTS.md](FAST_MODE_TESTS.md). These are local follow-up observations;
they have not been posted to the existing PR.

Local connection observations: initially weak discovery RSSI and connection
failures improved substantially after the owner installed the PC antennas.
Cached FA-service enumeration also allowed sessions in a previously failing
state, but cache use was not isolated from other conditions. No claim is made
that this identifies a Windows/Bleak/pypixelcolor bug. A controlled comparison
and direct upstream-client reproduction would precede any proposed fix.

Not established: physical maximum frame rate, maximum file size/frame count,
large-file persistent capacity, all slot/settings behavior, or support for every
production batch of article 3226274. Capacity files repeat 44 original animation
poses with distinct counters; these are not thousands of original poses. Original
256-KiB / 600-frame guards and later explicit 2-MiB / 4,096-frame test bounds
are software experiment limits, not measured device limits. The 4,096-frame test
succeeded within these bounds; the hardware ceiling remains unknown.

Would these observations be useful in a tested-device table or documentation?
We can provide small sanitized packet excerpts and an original numbered test
animation, plus a direct client reproduction after checking your preferred
test procedure.

## Before posting or preparing a PR

Detailed current evidence is in [LIBRARY_PANEL_TESTS.md](LIBRARY_PANEL_TESTS.md).
Finish pending probes and attach a minimal original fixture/reproduction before
posting; do not present reply-only timings as successful playback.

- Check for an existing model discussion/report and follow applicable repository
  templates; link to one canonical report rather than posting duplicates.
- Retain the distinction between the successful small public-client trial and
  adapter-based capacity/streaming evidence; do not generalize either to an
  untested public-API workload.
- Share only target-specific sanitized excerpts. Raw captures contain nearby
  devices and unique identifiers and are not ready to publish wholesale.
- Use our original diagnostic animation as a shareable fixture; exclude the
  downloaded eyes artwork whose reuse license was not stated.

## Secondary report

For `Pupariaa/Bk-Light-AppBypass`, offer a short model/label compatibility note
and link the canonical report. Be clear that its client and its different
legacy trailer were not directly tested. Do not claim a new protocol discovery.
No cross-post to unrelated protocol-family repositories is warranted by these
FA-family tests alone.

## Separate local code proposal: public chunk-size configuration

A focused local patch now adds optional `chunk_size` to `Client` and
`AsyncClient`, preserving default command sizes and acknowledged writes. It
includes validation, documentation, type stubs/generator templates and 28 new
regression cases; all 68 library tests pass. See
[../../patches/README.md](../../patches/README.md) for the standalone patch and reproduction.
This is separate from the compatibility report above and has been published as
[pypixelcolor PR #90](https://github.com/lucagoc/pypixelcolor/pull/90). The PR uses
the approved description, explains the image workload without the local game
name, and discloses AI assistance. Its CI workflow awaits maintainer approval.
The compatibility report above remains an unpublished draft.

Using the same patched public API, PNG sequence and connection defaults, a
two-minute Starfall run completed 1,175/1,200 scheduled updates at default chunks
and 1,200/1,200 at 500 bytes. P95 upload/API time fell from 112.602 to 90.951 ms.
The owner confirmed correct rendering with little visible difference; both
sessions received strict completion replies and disconnected. This later pair
changes only the public chunk-size option and does not use the adapter. It is
still one sequential comparison on one Windows host/panel, not a general speed
or compatibility claim. Full method/results are in
[STARFALL_STREAM_TESTS.md](STARFALL_STREAM_TESTS.md#public-chunk-size-patch-comparison).

This supports an opt-in configuration feature, not a new default or a switch to
unacknowledged transport. Other correctness observations should be proposed
separately with minimal reproductions.
