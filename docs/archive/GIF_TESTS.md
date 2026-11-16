# Panel-local GIF playback

Date: 2026-11-14. The verified 64×16 B.K. Light panel remained at the reported
approximately two-metre desk placement, on a separate USB supply, with PC
antennas installed. The phone app was not needed.

## Source and bounded format

The already-pinned [pypixelcolor image builder](https://github.com/lucagoc/pypixelcolor/blob/c8cbaebca6df7797a7bcface8a1c4ca33e499973/src/pypixelcolor/commands/send_image.py)
at commit `c8cbaebca6df7797a7bcface8a1c4ca33e499973` was inspected locally.
Its `_build_send_plan` uses opcode `03` and format marker `02` for GIF, compared
with `02` and `00` for the PNG path already verified on this panel. Both use
file size, standard CRC32, a 12-KiB window and a save-slot byte. The reference
describes slot 0 as non-saving; no persistent slot was used.

Our original encoder implements only a single GIF window:

```text
[total message bytes LE16] 03 00 00 [GIF bytes LE32] [CRC32 LE32] 02 00 [GIF]
```

The encoder rejects non-GIF signatures or payloads over 12 KiB. The generated
GIF itself was decoded and checked before hardware use: 64×16, twenty distinct
frames, each 200 ms, loop extension 0 (infinite), disposal 2, no transparency.
A fixed palette preserves the exact diagnostic pixels. Each image shows a yellow
sprite and white `01/20` through `20/20` counter, with END on the last frame.
The encoded loop duration is four seconds at 5 fps.

The reference's [AckManager](https://github.com/lucagoc/pypixelcolor/blob/c8cbaebca6df7797a7bcface8a1c4ca33e499973/src/pypixelcolor/lib/transport/ack_manager.py)
treats status byte 3 in a five-byte `05` notification as upload completion.
The experiment records the whole reply rather than presuming that GIF replies
must echo the outgoing opcode. The actual reply was `05 00 03 00 03`.

## Hardware result

One session used cached FA-service metadata and the already-tested information /
Berlin time and version exchanges. It uploaded the GIF once, received the reply,
then stopped notifications and disconnected. It sent no playback-start command,
individual animation frames or further application writes during observation.

| Measurement | Result |
| --- | --- |
| GIF / framed message size | 4088 / 4103 bytes |
| Message prefix | `07 10 03 00 00 f8 0f 00 00 ab ce 4c 42 02 00` |
| GATT chunks | 17: sixteen 244-byte chunks and one 199-byte chunk |
| First-to-last GATT write interval | 704.592 ms |
| First write to completion reply | 734.154 ms |
| Reply | `0500030003` |
| Last scan advertisement RSSI | -68 dBm, snapshot rather than live RSSI |
| Disconnected observation | 18:33:28.823–18:33:40.836 UTC / 19:33:28.823–19:33:40.836 CET |
| Observation duration | 12.013123 seconds |
| Application writes during disconnected observation | 0 |
| Upload failures / retries | 0 / 0 |

After observation finished, the owner was asked whether the counter kept cycling
01/20 → 20/20 → 01/20 and whether timing looked steadier or showed problems.
Owner response:

> It keeps looping; timing looks steady

**Confirmed: this GIF renders and loops locally after the host disconnects.**
The owner reports steady-looking timing. Exact frame durations and loop period
were not instrumented on the physical display; 5 fps describes the encoded GIF.
The file remains playing after the test. Replacing it with another tested PNG or
GIF operation is available; power-cycle persistence, flash behavior, persistent
slots and maximum playback rate remain untested. Later multi-window results are
linked below.

The 17 transmitted chunks were reconstructed offline and matched the generated
GIF/CRC packet exactly. This verifies one small local animation, rather than a
general GIF compatibility claim.

Later follow-up: [EYES_BENCHMARK.md](EYES_BENCHMARK.md) records real online art
and the source-backed multi-window implementation. The owner confirmed a
44-frame, 20,500-byte two-window GIF worked. A seven-window rate comparison
rendered all encoded 10/20/25/50 fps sections with owner-reported increasing speed.
A twenty-window 528-frame / 244,687-byte GIF at encoded 20 fps also played through
to 528 and looped correctly after disconnect. The original single-window result
above is preserved; hardware capacity and exact playback-rate ceilings remain unknown.

Private evidence:

- `captures/gif-local-20261114.jsonl`
- `captures/gif-local-20261114.gif`
- `captures/gif-local-20261114-console.txt`
- `captures/gif-local-20261114-observation.md`

## Reproduce

With the identified panel in `$deviceId`, use new output filenames:

```powershell
.\.venv\Scripts\python.exe examples\gif_animation.py $deviceId --windows-cached-services --output captures\gif-new.jsonl --preview captures\gif-new.gif
```

The example generates the GIF before connecting, uploads it once, disconnects,
and waits twelve seconds before its `finished` event. Visual questions follow
that event. It performs no automatic retry. Automated verification: 113 tests
passed, including decoded frame-by-frame pixel equality, durations/disposal/loop
metadata, GIF CRC/header and size rejection. Tests use no hardware.
