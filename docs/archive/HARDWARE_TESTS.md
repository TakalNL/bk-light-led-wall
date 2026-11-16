# First-contact hardware checklist

Status on 2026-11-14: panel-on/off/on scans identified the target and a later
metadata-only GATT inspection **succeeded**. The owner powered the panel from
the PC's USB port; the rescan reported -86 dBm, versus earlier -96 to -98 dBm.
The successful inspection was outside the execution sandbox. Earlier attempts
returned device-not-found in the sandbox and GATT unreachable on the host; their
cause remains unverified. Do not infer an antenna defect or supply problem.
Windows reports an Intel Wireless Bluetooth adapter with status OK.
The metadata inspection sent no application commands or notification subscriptions.
Subsequently, a bounded reference pixel experiment and an owner-requested repeat
sent three color commands each and observed FA03 notifications (none received).
The owner confirmed the repeat changed one corner pixel red/green/blue: **the
first Python pixel milestone is achieved**. Identifiers remain in private captures;
protocol evidence is recorded in `PROTOCOL.md`.
Owner reports B.K. Light `3226274 | 37/2026`, companion app **iPixel Color**.
The owner has an iPhone and has not installed the app; the successful experiment
did not use a phone application.

Next-stage results: the information reply returned type `0x83`, consistent with
the references' 64×16 grid, and version pairs `[14,2]` / `[7,4]`. The owner then
confirmed all four corner markers at their expected physical edges, verifying
64×16 with a top-left origin. A single static raw RGB diagnostic frame was sent,
but the owner saw startup artwork rather than the test image. The PNG/CRC path
is the follow-up candidate. Its first two attempts failed during GATT service
retrieval, before sending application commands; the owner then power-cycled the
panel before another attempt. That attempt also failed before writes. A read-only
Windows diagnostic then connected using cached FA-service metadata. With that
explicit workaround, the PNG upload succeeded and the owner confirmed the border,
colored corners, text and RGB bars. **The static-image milestone is achieved.**

## First contact

- [ ] Record label/controller markings, app version and phone OS. Preserve `37/2026`
  literally until its meaning is established. Record USB adapter rating.
- [x] Verify grid using the hardware type reply and physical corner markers:
  64×16, superseding the brief's unverified 16×51. The owner confirmed all four
  proposed markers at the outer edges; no controller disassembly was needed.
- [x] Use one panel and USB power near a BLE-capable computer (owner used PC USB).
- [ ] Close/disconnect iPixel Color to free a possible single BLE connection.
- [x] With panel off, save a 15-second scan (`scan-off-20261114.json`).
- [x] Power the panel on and save new scans (`scan-ready-20261114.json`,
  `scan-return-20261114.json`, later `scan-pc-usb-20261114.json`).
- [x] Compare names/identifiers/services and repeat off/on if identification is
  uncertain. RSSI alone cannot identify a device; addresses can change.
- [x] Select the panel's current identifier explicitly. Save one GATT inspection
  to `captures/gatt-pc-usb-20261114.json`. No handshakes or value writes.
- [x] Record writable and notify/indicate characteristics, handles and services.
  Compare with the research fingerprints without calling this compatibility proof.
- [ ] Optionally select one observed notification characteristic and capture for
  30 seconds/100 events. This enables its CCCD; no display command is sent.
- [ ] Record any connection prompts/errors, spontaneous messages, display changes,
  and whether the phone app reconnects after the PC disconnects.

Exact PowerShell commands (use fresh filenames for repeats):

```powershell
.\.venv\Scripts\led-matrix.exe scan --timeout 15 --output captures\scan-off.json
# Power on the panel, then:
.\.venv\Scripts\led-matrix.exe scan --timeout 15 --output captures\scan-on.json
$deviceId = 'REPLACE_WITH_IDENTIFIED_PANEL_IDENTIFIER'
.\.venv\Scripts\led-matrix.exe inspect $deviceId --output captures\gatt.json
# Optional: use a full UUID or handle actually reported as notify/indicate:
$notifyUuid = 'REPLACE_WITH_FULL_UUID_FROM_INSPECTION'
.\.venv\Scripts\led-matrix.exe listen $deviceId --characteristic $notifyUuid --duration 30 --max-events 100 --output captures\notifications.jsonl
```

If no BLE candidate appears, repeat after checking power/adapter/app connection.
Inspect OS discovery and the official app's transport/HCI log separately for
Classic traffic. Do not infer Classic from one failed BLE scan. Log the outcome.

## Official-app capture procedure (next stage)

This procedure is prepared, not tested on the owner's phone. AOSP describes
[Bluetooth debugging and snoop logging](https://source.android.com/docs/core/connect/bluetooth/verifying_debugging).
Vendor access varies; not every device exports usable full logs.

1. Record Android/device/app versions and host/phone UTC time. Use Android
   Developer options to enable **Bluetooth HCI snoop log** (full logging if
   offered); restart Bluetooth if required by the device. Keep the interval short.
2. Start with a known app/display state. Connect with the official app only;
   the PC's BLE client must be disconnected. Record the connection experiment.
3. Perform exactly one controlled action, note the UTC time and visible result,
   wait briefly, then disconnect. Repeat with separate experiment IDs.
4. Enable USB debugging, authorize your computer and use Android platform-tools:
   `adb devices`, then `adb bugreport captures/android-bugreport.zip`.
   Review the archive for `FS/data/misc/bluetooth/logs/btsnoop_hci.log` or vendor
   equivalents. Direct `adb pull` from `/data/misc/...` is often denied on normal
   phones. Do not root a phone just to obtain this first capture.
5. If the archive contains only abbreviated btsnooz data, AOSP's linked
   `btsnooz.py` can extract it from the text bugreport. Record missing/truncated
   data as a limitation; do not invent the absent packets.
6. Turn snoop logging and USB debugging off when finished. A bugreport can contain
   unrelated personal data; keep the original private and share a target-only
   extract where possible.
7. Open the HCI log in Wireshark. Start with `btatt`; identify the target ACL
   connection, then its service discovery/UUID-to-handle mapping. Handles are
   connection/device-specific; don't copy handles from someone else's capture.
8. Inspect ATT writes/notifications and long-write preparation/execution. Useful
   display filter: `btatt.opcode == 0x12 || btatt.opcode == 0x52 ||
   btatt.opcode == 0x16 || btatt.opcode == 0x18 || btatt.opcode == 0x1b ||
   btatt.opcode == 0x1d`. Also retain surrounding responses/discovery in the
   original. Filter to the target connection before exporting.
9. Export selected packet dissections **including bytes**, and record each
   action using [../../captures/experiment-template.csv](../../captures/experiment-template.csv).
   Optional CSV extraction using installed TShark (no new Python dependency):

   ```powershell
   tshark -r captures\btsnoop_hci.log -Y btatt -T fields -E header=y -E separator=, -e frame.number -e frame.time_epoch -e btatt.opcode -e btatt.handle -e btatt.value
   ```

10. Compare lengths and changing bytes across repeated actions; reconstruct
    application messages across ATT fragments before inferring CRCs/headers.
    Distinguish application payloads from HCI/L2CAP/ATT headers. Add observations
    with confidence labels to `PROTOCOL.md`.

Wireshark's [Bluetooth ATT field reference](https://www.wireshark.org/docs/dfref/b/btatt.html)
documents the fields used above. This is offline inspection; nothing is replayed.

## Controlled experiment order

Start with connect/disconnect. Then use the app for display off/on; solid red,
green, blue, white, black; one pixel; horizontal/vertical lines; one brightness
step; two distinct images; and a short animation. Keep one variable per capture.
Maintain a fixed orientation/brightness except in experiments changing them.
Do not use firmware updates, password changes, resets or unexplained commands.

For the pixel experiment, use one known coordinate inside the verified dimensions,
a fixed background and two colors. Record the prior state, action timestamp,
characteristic, transmitted bytes, packet length, response and visible behavior.
An app may upload a full image even when only one pixel changes.

## Results

| Experiment | Result | Next decision |
| --- | --- | --- |
| Packaging, CLI and simulated BLE tests | See README / automated test report | Ready for owner-operated first contact |
| Initial on/off/on scans | Named LED candidate disappeared while off and returned at the same address when on | Target identified |
| PC USB rescan | Same target, RSSI -86 dBm | Attempt metadata-only connection |
| GATT metadata | Success outside sandbox: 00FA / FA02 write and FA03 notify; AE00 also present | Candidate iPixel interface confirmed; capture packet semantics next |
| Official-app single-pixel capture | Pending | Decide whether/how to replay |
| First Python pixel | Achieved: three published FA02 pixel writes at (0,0), RGB sequence confirmed by owner during eight-second repeat; no application notifications | Complete; followed by grid test |
| Device information | Type 0x83, reference 64×16; MCU bytes [14,2], secondary [7,4]; MTU 517 | Check physical edges with markers |
| Corner mapping | Red TL, green TR, blue BL, yellow BR confirmed by owner at edges | 64×16 and orientation verified |
| One static raw RGB image | 3081-byte raw frame, 13 completed writes, reply 0500000001; owner saw default startup artwork | Failed visual result; stop using raw mode as a supported path |
| Initial PNG/CRC attempts | GATT-unreachable failures before any application writes | Retry after owner power cycle |
| PNG after power cycle | GATT enumeration still unreachable; no application writes | Diagnose host enumeration separately |
| Read-only Windows cache diagnostic | Allowed access; known FA-service layout connected from cache at MTU 517 | Opt into cached metadata for the supervised image test |
| PNG static image | 506-byte PNG, 521-byte CRC frame in three chunks; `0500020003` reply; owner: Yes, all correct | Static image verified |
| PNG sprite streaming | Twenty frames at 2 fps over 10.006 seconds; 20 expected replies; owner confirmed regular movement and END with no glitches | Bounded host streaming verified; higher rates and sustained runs untested |
| Numbered PNG sprite at 5 fps | Fifty frames over 10.004 seconds; 50 expected replies; owner confirmed counter progression to 50/50 and END with no glitches | Bounded 5 fps streaming verified; higher rates and sustained runs untested |
| One-minute numbered sprite at 5 fps | 300/300 expected replies over 60.003 seconds, no retries or connection failures; owner saw all frames with possible uneven pacing | Minute streaming verified; uniform screen timing and longer runs unverified |
| Panel-local numbered GIF | One 4088-byte GIF, 17 GATT chunks, reply `0500030003`; owner confirmed continuing loops and steady-looking timing after PC disconnected | Local GIF playback verified; power-cycle persistence and exact screen timing untested |
| Online eyes, 44 frames | Native 64×16 GIF, 100 ms encoded delays, two upload windows; owner confirmed steady correct motion and counter loop | Multi-window GIF upload verified; rate/capacity follow-up in EYES_BENCHMARK.md |
| Online eyes, four rates | One 176-frame GIF with encoded 10/20/25/50 fps sections, seven windows; owner confirmed all four worked and looked progressively faster | Qualitative rate comparison complete; exact physical fps unmeasured |
| Online eyes, 528 frames | 244,687-byte GIF, encoded 20 fps, twenty windows, no retries/errors; owner confirmed counter reached 528 and looped after disconnect | This frame count and file size work; upper capacity limit unknown |
| Actual-library capacity | 1,024-, 2,048- and 4,096-frame GIFs visually confirmed; largest 1,915,364 bytes, 156 windows, encoded 204.8-second loop | Working lower bound; hardware maximum unknown |
| Slot-1 retention | Original twenty-frame GIF resumed automatically after boot animation following an owner-performed power cycle | Small-fixture retention/startup verified; large persistent capacity unknown |
| Compact RGB live stream | 100/100 numbered frames at scheduled 10 fps visually confirmed; 15/20 fps probes stopped at timing cutoffs | Short 10 fps improvement verified, not physical FPS ceiling |
| Same-session coordinate edits | Add green beside red, erase red with black, green remains; visibly sequential | Partial pixel-drawn edits work; no atomic rectangle or PNG overlay established |
| Fast transport probes | Fast GIF and native-pixel animation visibly failed despite completed writes/replies | Unsupported paths; acknowledged recovery restored known GIF |

Information still needed: controller chipset, meaning of all version/response
fields, large persistent capacity and additional slot behavior. App version/capture availability is
optional while published operations can be validated directly on hardware.
The first pixel was reproduced directly from two agreeing inspected references
after verifying the GATT interface. A captured official-app operation remains
useful for richer commands, but was not needed for this bounded experiment.
Initial experiments disconnected before visual observations; later drawing-state
tests kept one connection open to avoid reconnect display changes. Grid mapping
and static PNG rendering are complete. The single compressed frame transferred
in about 150 ms excluding connection/setup, but no sustainable animation rate
is established by that static transfer. The subsequent paced sprite experiment
verified ten-second passes at 2 fps and then 5 fps with a visible frame counter,
documented in [ANIMATION_TESTS.md](ANIMATION_TESTS.md). A subsequent one-minute
5 fps run delivered all 300 frames, with owner-reported possible uneven pacing.
The later compact RGB path achieved a short, visually confirmed 10 fps pass;
uniform physical screen timing and runs beyond one minute remain unmeasured.
The subsequent [local GIF experiment](GIF_TESTS.md) verified a
short numbered loop kept playing after disconnect, with owner-reported steady
timing. Later slot-1 power-cycle retention and library-based capacity/partial
results are in [LIBRARY_PANEL_TESTS.md](LIBRARY_PANEL_TESTS.md).

## Range follow-up

The user requested PNG reliability at a farther placement before animation.
At an approximately two-metre desk placement on a separate USB
supply, three independent trials all failed before application writes: one scan
miss, two connection/setup timeouts with last advertisement RSSI -101 dBm.
Cached services were enabled for all attempts. The owner confirmed the panel was
lit. Since power source and position changed together, those initial failures
did not isolate the cause.

The owner then reported installing the PC antennas and requested another test
at the same desk with the same separate supply, deferring the near-PC comparison.
ANT1, ANT2 and ANT3 all connected, uploaded and received `0500020003`, without
retries. Last advertisement RSSI was -67, -69 and -74 dBm; connection/setup after
each scan took 0.731–0.871 seconds and PNG writes took 89.6–119.6 ms. The owner
confirmed the final ANT3 image and complete diagnostic pattern after disconnect.
Earlier ANT images were not separately confirmed visually. Reception is strongly
implicated. The later one-minute streaming run also kept its connection, while
longer-duration reliability, maximum range and fresh uncached GATT enumeration
after the antenna change remain untested. See
[RANGE_TESTS.md](RANGE_TESTS.md) for captures and timing definitions.
