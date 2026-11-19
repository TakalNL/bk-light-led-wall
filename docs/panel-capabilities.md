# Panel capability map

Date: 2026-11-19. Broad static survey of iPixel Color Android 3.7.9, combined
with existing observations on the owner's two panels. This is an inventory of
the app-exposed surface and current evidence, not a complete firmware audit.
The initial survey was static. A subsequent bounded top-panel experiment is
recorded below; visual behavior is kept separate from successful GATT writes.

## Evidence levels

- **Verified:** previously exercised on the owner's hardware, with the limits
  recorded in the linked reports. Verification on one panel is not silently
  extended to every panel or every parameter.
- **App command:** an actual packet builder or sending path is present in the
  readable APK. The described function remains untested on the owner's panels.
- **Phone feature:** app-side computation or content generation feeds a display
  command. This does not demonstrate equivalent standalone firmware behavior.
- **Unresolved:** model gates, reachability, semantics or physical support still
  need tracing or a bounded hardware test.

The target profile is 64x16, device type `0x83`, customer `0007`, product `04`,
owner-displayed MCU 14.02 and Bluetooth 7.04. The shared advertising selector was
recovered from both units; the owner's device-info screenshot text was not
assigned to a particular panel. See [compatibility](compatibility.md),
[AE00 identification](ae00-identification.md), and
[firmware metadata](firmware-metadata.md).

## Function inventory

| Area | App-exposed functions and mechanism | Evidence on these panels |
| --- | --- | --- |
| Device identity | iPixel device-type/time exchange and hardware-version query | Verified type/grid and version byte pairs. The type query also writes the clock. |
| Basic display | On/off, brightness, hardware orientation, exit current display mode | App commands. Hardware orientation is separate from our software rotation. Parameter ranges and persistence remain untested here. |
| Still images | PNG upload, program/slot destination, host-rendered content | RGB PNG verified. A tested indexed PNG displayed black despite a successful upload reply. |
| Local animation | GIF upload, multi-window transport, program/slot destination | Verified disconnected looping. A 4,096-frame / 1,915,364-byte GIF worked; this is a lower bound, not a capacity ceiling. Exact physical FPS remains unmeasured. |
| Saved content | Persistent slot and startup playback, program-list uploads/deletion | One small slot-1 GIF survived one power cycle. `08 80` program-list declaration replied but left BASE visible. A six-byte business command triggered resident scrolling content; arbitrary cached-content selection remains unresolved. See resident-playback follow-up below. |
| Pixel editing | Native DIY/pixel mode and coordinate/RGB updates | Static grouped drawing verified, including a full native two-square baseline. Mode 3 plus painting did not preserve the preceding PNG background. Fast animation remains limited by prior failures. |
| Native image operations | DIY mode branches for erase, horizontal/vertical mirror and whole-image movement | Recovered builders tested on the top panel: no visible horizontal swap or rightward shift established. Vertical mirror and erase remain untested. See bounded DIY results below. |
| Additional image path | `sendUnRedoImageData` uses internal data kind 6, sharing wire bytes `00 00` with kind 0 | App command; payload differences and codec/semantics remain unresolved. Do not infer hardware support from the method's name. |
| JPEG frame output | Camera/game paths feed JPEG-compressed bitmap bytes into `sendCameraData`, wire kind `00 00` | One recovered-format JPEG test returned `0500000001`, but the owner saw the default boot image. Correct JPEG rendering not demonstrated. |
| Text | Encoded text data, motion/effect attributes, speed, emoji, gradients and multilingual bitmap generation | App command plus phone-side shaping/rendering. Full language/effect support and storage limits are untested here. |
| Mixed content | Text/image regions, templates, border/background effects, composite GIF generation | Native region descriptors recovered in the `04 00` path. One candidate text/PNG preview showed the default image; rendering, codec assignment and entry requirements remain unresolved. Other paths generate media on the phone. |
| Clock/calendar | Clock style/mode, date/year/month/day and weekday fields | First style verified on top panel: green time, blinking colon, animated character; minutes advance after BLE disconnect. Eight styles exposed for this model in Android. Other styles, date display, accuracy and power-loss retention untested. |
| Countdown | Control byte, minutes, seconds; reset/start/pause/resume | Owner confirmed TEST remained after the held top-panel 05:00 reset/start sequence. No application replies; no countdown or autonomy demonstrated. |
| Stopwatch | Dedicated chronograph control command; reset/start/pause/resume | Owner reported the default LED image after the held reset/start sequence, rather than a counter. No application replies. Exact triggering step and broader support remain unresolved. |
| Scoreboard | Two little-endian 16-bit score values sent by a dedicated command | Owner confirmed TEST remained after the top-panel 12/34 command: no visible scoreboard transition in this tested state. No application reply; broader support remains unresolved. |
| Alarms | Numbered alarms, weekday mask, hour/minute, duration and content | App command; actual RTC execution, capacity, persistence and sound are unverified. A UI limit is not a measured storage ceiling. |
| Scheduling | Numbered weekday/time records and a buzzer-enable field | App command; autonomous execution and presence of a physical buzzer are unverified. |
| Music visualization | Rhythm settings and amplitude/spectrum data commands | Phone music/recording callbacks feed panel commands. No built-in panel microphone or audio decoder has been established. |
| Camera/video | Camera decode and video-to-GIF/frame conversion | Phone feature feeding the raw/media paths. Not evidence of an on-panel camera or video-file decoder. |
| Games | Snake, Pong and Tetris game views | App game screens render frames and call `sendCameraData`; this is evidence of phone-driven games, not dedicated on-panel game engines. Our own PC games already work through RGB PNG streaming. |
| Riding | Riding mode, device-sensor service and `sendSportData` | App/sensor feature with a dedicated output packet. No on-panel GPS, accelerometer or speed sensor has been established. |
| Remote-control screens | Business and eye presets route text/images/GIFs and program actions | Business button-1 packet `060007800100` triggered resident scrolling content with no media upload. Button 2 also triggered scrolling, but a distinct selection was not confirmed. No physical remote receiver established. |
| Credentials | Set and verify a display password; credential length varies in code | App command. Not tested or changed on the owner's units. |
| Clear/delete | Clear all display data and delete selected program indexes | App command. Not exercised in this survey. |
| Two BLE outputs | `BleManager` and `BleManager2`, parallel sets of sending helpers | Two simultaneous PC links already verified. Current Android picker explicitly excludes `0007/04` from dual-eye connections; see below. |
| Paired-eye coordination | Upload separate eye data, retain short headers, send left/right synchronization data | Short-header GIF restart verified. Concurrent restarts brought deliberately offset loops into close visible alignment; owner reports a small, steady bottom-panel lead. Deferred upload start was not observed. See below. |
| Wi-Fi | Separate connection state, socket transport and Wi-Fi output paths | Generic app support only. No Wi-Fi interface has been established on the owner's panels. |
| Firmware service | AE00/AE01/AE02, authentication and RCSP identity | Verified on both. Target info reports protocol 2.0; feature-map responses contain no bitmap. |
| Firmware updates | JieLi OTA wrapper plus other MCU/Wi-Fi update builders | Code present; no update attempted. Dual-bank support is a reported flag, not an exercised update mechanism. |
| Firmware metadata | Product/version-specific signed and legacy HTTP lookup | Recovered and exercised; all four bounded requests returned no matching data. No firmware image obtained. |
| Capacity/performance | File size/frame count, transport rate, refresh, response timing | Only measured lower bounds and bounded tests exist. No hardware FPS, maximum panel-count or flash-capacity ceiling is established. |

## Wire-command index

The values below are the **two bytes at packet offsets 2 and 3**, in wire order,
not big-endian command numbers. They are extracted from packet-building code;
listing them is not a claim that every command is supported on this profile.
Packet layouts and model-dependent branches must be checked before use.

| Bytes | Builder / family | Status |
| --- | --- | --- |
| `01 80` | `SendCore.getLedType`, `getLedType2`: type/time exchange | Verified, with clock side effect. |
| `05 80` | `SendCore.getHwInfo`: MCU/secondary version query | Verified. |
| `02 00` | PNG/image upload family | Verified for tested RGB PNGs. |
| `03 00` | GIF upload family, including program and eye variants | Normal GIF verified; variants unresolved. |
| `05 01` | Native DIY pixel data kind | Slow coordinate edits verified; fast use limited by failures. |
| `00 00` | Camera/game frame kind, also used by internal kind 6 | At least Pong bitmap/CameraX paths send JPEG, without CRC in kind 0. One JPEG test failed visually despite a reply. Payload identity must be traced per caller. |
| `04 00` | Internal data kind 7: native template/region container | Builder contains separate region descriptors/data. Candidate preview failed visually; support remains unresolved. Not the `sendUnRedoImageData` kind. |
| `00 01` | Text data kind | App command; attribute layout/model coverage pending. |
| `03 01` | `setTextSpeed` | App command. |
| `04 01` | `setDiyFunMode` | DIY mode; not established as dual-display pairing. |
| `01 01` | `sendExitCmd` | Exit-mode command, not evidence of GIF pause. |
| `07 01` | `sendLedOnOff` | App command. |
| `04 80` | `setLedLight` | App command. |
| `06 80` | `setUpsideDown` | App command. |
| `06 01` | `sendColockMode` | First clock style visually verified, including minute advancement while disconnected. |
| `12 80` | `setWeek` | Writes weekday; not a read-only query. |
| `0a 80` | `setScoreboard` | Two score values. |
| `09 80` | `setSecondChronograph` | Chronograph control. |
| `0d 80` | `setCountDown` | Control, minutes, seconds. |
| `00 80` | `payLoadAlarmClockData` | Alarm record/content upload. |
| `11 80` | `sendTimingData` | Scheduling record. |
| `00 02` | `sendRhythm` | Two rhythm settings. |
| `01 02` | `sendRhythmChart` | Style plus derived level/bar data. |
| `06 00` | `sendSportData` | Three riding-mode fields. |
| `04 02` | `setPwd` | Password-related write; format branches exist. |
| `05 02` | `verifyPwd` | Credential verification; format branches exist. |
| `03 80` | `deleteAllData`, `deleteAllData2` | Destructive clear; not tested here. |
| `02 01` | `sendChannelDelIndex` | Delete program indexes; not tested here. |
| `08 80` | Program-list declaration from channel/template UI | Tested list containing program 1 returned `0500088001` without a visible transition. App proceeds to media uploads after this reply. |
| `07 80` | Business-remote button and language selection | Six-byte button-1 command triggered resident scrolling content; custom bank mapping and distinct button selection remain unresolved. |

Template/program metadata and firmware-transfer builders have additional
structures and model branches; they are retained in disassembly rather than
reduced to misleading single-opcode recipes. This table is a reviewed subset
of the full method inventory, not an exhaustive firmware opcode table.

## Newly found two-panel path and its limits

The readable build contains `BleManager2`, secondary `sendCompat2` routing,
paired GIF/text/image helpers, and `SendCore.sendEyeData`.
`sendSynchronization` sends `leftSynData` through the primary transport and
`rightSynData` through the secondary transport. Those are two consecutive host
calls, not evidence of atomic firmware display swaps or a shared refresh clock.

In the conditional eye-upload path, the code changes header byte 14 to decimal
101 (`0x65`), saves the first 15 bytes, and replaces the saved packet's length
with 15. After upload callbacks, the app can resend the two saved short headers
through `sendSynchronization`. The follow-up below verifies these short headers
as cached-GIF restart controls on the tested panels. The upload did not wait for
them before playing. Exact display onset and two-panel drift after disconnect
remain unmeasured.

Both the older `ConnectDialog.isEyesScreen` and the **current**
`ChooseActivity.isEyesScreen` return false for customer `0007` with product `04`
or `01`, before checking eligible display types. Our panels match `0007/04`.
The current `safeShowConnectDialog` constructs `NewConnectDialog`; its listener
`ChooseActivity$safeShowConnectDialog$1$1.onStateClickListener` calls the current
check and disconnects an existing primary/secondary device when it returns
false. The delayed connection callback fills the primary link first and the
secondary only when the primary remains occupied. Thus the exclusion is on the
active Android 3.7.9 picker path, not just dormant legacy code. It explains the
Android connection policy; the iPhone source was not inspected.

In the current check, the product/customer match branches directly to `return
false` (`002e` to `005e`), independent of size. Separately,
`ChooseActivity.setLedType` maps our advertised `0x83` (signed byte -125) to
internal app display type **3** (`0196` through `01aa`). An app type number is
not an additional firmware capability flag.

The app contains a real two-output coordination implementation, but the current
Android picker excludes this product. The subsequent hardware tests below
verified cached-GIF restart and close visible two-panel alignment, while
leaving deferred activation, atomic swaps and shared-clock behavior unproven. The
earlier paired-artwork-only explanation is provisional and must not be used
to close this investigation.

### Paired-eye preview and restart: hardware follow-up

`DevilsEyeFragment.sendGif` explicitly passes `isDown=false`; its default mask
`0x22` supplies an empty metadata header and serial byte zero, without replacing
that false flag. `SendCore.sendEyeData` creates GIF packets through
`payloadChannel`, changes byte 14 to `0x65` for this preview path, and retains
the first 15 bytes with length changed to 15. The primary and secondary
completion callbacks set their respective completion flags on final status 3;
whichever sees both flags calls `sendSynchronization`. That method issues the
saved primary and secondary headers as separate host sends.

The research helper `.research/eye_preview_observation.py` reconstructs the
one-window packet independently and checks it against the pinned upstream
builder before changing byte 14. Its four-frame 64x16 GO0..GO3 GIF has encoded
700 ms frame durations, length 2,353 bytes, CRC32 `3faf7e39` (wire little-endian
`39 7e af 3f`), SHA-256:
`7fa6d8cc2126068626316f694109c85aed713ba70849d9b65b2787d62e81d99a`.
The full upload header is `40 09 03 00 00 31 09 00 00 39 7e af 3f 02 65`.
The short restart is `0f 00 03 00 00 31 09 00 00 39 7e af 3f 02 65`.

Three single-panel stages were observed:

1. **Upload without short header:** top panel first showed the HOLD PNG, then
   played GO0..GO3 before any activation header was sent. Upload returned strict
   completion `05 00 03 00 03`. This tested path does **not defer playback** on
   this firmware. Capture: `captures/eye-preview-observation-20261119T161618Z.jsonl`.
2. **One short header:** repeating the upload and sending the 15-byte header
   returned `05 00 03 00 03`; the owner still saw GO0..GO3. That observation
   alone did not determine whether the loop restarted. Capture:
   `captures/eye-preview-observation-20261119T161808Z.jsonl`.
3. **Repeated short headers:** the same 15-byte header was sent 80 times, with
   recorded host intervals 1.039–1.083 seconds, below the GIF's encoded time to
   reach GO2. The owner saw **only GO0 and GO1**, having previously seen all four
   frames. This establishes that these headers restart playback of the already
   uploaded GIF in this tested state. Capture:
   `captures/eye-preview-observation-20261119T162005Z.jsonl`.

The first stage's attempt to advance the observation failed on a control-file
UTF-8 BOM. The helper exited the mode and restored the wall; **no short header
was sent in that capture**. The reader was corrected to accept UTF-8 BOM and
control writes changed to atomic replacement before stages 2 and 3. This error
does not invalidate the owner's pre-activation playback observation.

`.research/eye_pair_observation.py` then connected both panels and queried
their identity/version information. Both reported type `0x83` and version
bytes `[14,2]` / `[7,4]`. It uploaded the same preview GIF to the top panel,
inserted a 1.4-second delay, and uploaded it to the bottom panel. The owner
confirmed that their numbers were **not in sync**. It then submitted one
15-byte header to each link concurrently. Both returned `05 00 03 00 03`.

The owner reported **"pretty close to synced up perfectly"**, then clarified
that the bottom panel had a **small, steady lead**, rather than an increasing
lead. This verifies close visible alignment from coordinated cached-GIF
restarts during this observation period. The owner-estimated few milliseconds
are not an instrumented LED timing measurement. No further animation frames or
restart headers were sent during the aligned observation. Capture:
`captures/eye-pair-observation-20261119T162208Z.jsonl`.

| Recorded host quantity | Value | Limit |
| --- | --- | --- |
| Restart application data | 15 bytes per panel, 30 total | Excludes BLE framing and replies |
| Difference between host restart submissions | 0.482 ms | Host scheduling, not LED onset |
| Difference between GATT write completions | 2.240 ms | Host/backend completion, not LED onset or visible offset |

The restart is therefore a verified additional control capability despite the
app's connection-picker exclusion. This is **not** evidence of an atomic
two-panel display swap, shared refresh clock, measured sub-frame alignment,
long-term drift behavior or restart without a preceding compatible upload.
No power-cycle persistence or storage-slot interpretation was tested for
`0x65`. The normal wall controller has not been switched to this mechanism.

After the owner confirmed the small, steady lead, the helper exited the test
mode on both panels and finished normally. The ring controller was restored;
`captures/wall-ui-20261119-172601-169410.jsonl` records both connections,
`wall_ready` at 64x35 and subsequent frames acknowledged by both panels.
`.research/panel-capabilities/eye-coordination-audit.json` retains the computed
host timing values and explicitly marks physical timing as unmeasured.

## Bounded native-mode follow-up

The script `.research/native_modes_probe.py` addresses only the top panel
`95:53:D1:21:30:2F`. It uses a fixed allowlist and records every write and
notification in `captures/native-modes-top-20261119T155609Z.jsonl`.
Initialization confirmed type `0x83` and version reply `080005800e020704` on
that panel. Initialization also synchronized its time of day.

The packet layouts were checked against `SendCore` and the UI click handlers.
`ByteUtils.short2Bytes` returns high byte first, but `setScoreboard` reverses
each pair: scores are little-endian on the wire. The pinned upstream
`set_scores(12, 34)` and `set_timer(0/1/2)` builders match the tested bytes.
Android additionally uses action **3** to resume a paused stopwatch; the pinned
upstream `TimerAction` exposes only 0, 1 and 2.

| Test | Packet bytes | Intended observation |
| --- | --- | --- |
| Scores 12 / 34 | `08 00 0a 80 0c 00 22 00` | Two visible scores |
| Countdown reset | `07 00 0d 80 00 00 00` | Reset countdown |
| Countdown start, 00:30 | `07 00 0d 80 01 00 1e` | Descending time; 35 seconds with BLE disconnected |
| Stopwatch reset/start | `05 00 09 80 00` / `05 00 09 80 01` | Ascending time; 25 seconds with BLE disconnected |
| Stopwatch pause/resume | `05 00 09 80 02` / `05 00 09 80 03` | Eight-second pause, then resumed count |
| Exit mode | `04 00 01 01` | Cleanup before restarting the wall controller |

The Android countdown UI passes **control, minutes, seconds**, not hours,
minutes and seconds. Its control values are 0 reset, 1 start, 2 pause and 3
resume; only reset/start are included in this first countdown test. Stopwatch
pause/resume are included separately.

GATT writes completed, but the tested native mode commands produced no FA03
application replies in the two-second capture window after each write. Device
information queries did reply through the same notification subscription.
Neither GATT completion nor silence proves rendering, support or rejection.
The initial timed batch remained **sent, visually unverified**, including
autonomy during the disconnected intervals. Subsequent held observations are
recorded below and do not retroactively verify that initial batch.

The capture audit confirmed all ten expected native writes and their capture
windows, both disconnected intervals, and normal completion. Cleanup reset the
stopwatch and sent exit-mode. The ring controller was restarted afterward;
`captures/wall-ui-20261119-165831-383372.jsonl` records both connections,
`wall_ready` for the 64x35 canvas, and resumed frames with replies from both
panels. Physical appearance remains an owner observation.

The owner subsequently reported seeing only the restored wall demo and did
not observe the short test sequence. It provides no visual confirmation for
any native mode. Follow-up observations therefore use one test at a time,
leaving the output in place until the owner replies.

The first held test, `.research/scoreboard_observation.py`, paused the wall
controller, uploaded an RGB PNG reading **TEST** inside a cyan border to the
top panel (strict image completion reply `0500020003`), then sent the 12/34
scoreboard packet. That packet again produced no application notification in
two seconds. The script disconnected without restoring the demo so the owner
can inspect the result. Evidence:
`captures/scoreboard-observation-20261119T160040Z.jsonl`. A retained TEST marker
would establish no visible scoreboard transition in this tested state; a
rendered scoreboard would confirm that particular native mode. The owner
reported **"I only see TEST"**. This confirms the known image path rendered,
and that the scoreboard packet caused no visible transition in this tested
state. It does not establish that every scoreboard parameter or entry sequence
is unsupported.

The next held observation uses `.research/stopwatch_observation.py`: confirm
the top panel's version reply, send stopwatch reset and start, then disconnect
without reset or demo restoration. The TEST baseline is retained from the
owner's confirmed image. A counting display would demonstrate native execution
after disconnect; unchanged TEST would show no visible transition for this
sequence. Capture: `captures/stopwatch-observation-20261119T160157Z.jsonl`.
The owner reported **"i see the LED defalt image"** after this sequence. The
result was therefore neither the TEST baseline nor a reported stopwatch.
There is no visual confirmation of stopwatch execution or autonomy. Since
reset, start and disconnect preceded the observation, the transition cannot
be assigned to one of those steps from this experiment alone.

The following held observation, `.research/countdown_observation.py`, uploads
the fresh RGB TEST baseline, sends countdown reset, then starts **05:00** with
`07 00 0d 80 01 05 00`, and disconnects. Five minutes gives the owner time to
inspect the result; the controller does not restore the wall demo automatically.
Capture: `captures/countdown-observation-20261119T160309Z.jsonl`. The owner
reported **"TEST"**, confirming no visible countdown transition after this
sequence. Countdown execution and autonomous timing were not demonstrated.

After this result, the tested countdown/stopwatch modes were reset and
exit-mode sent, with all three GATT writes completed and no FA03 application
replies. Capture: `captures/native-modes-cleanup-20261119T160405Z.jsonl`.
The wall controller was restored. Its capture
`captures/wall-ui-20261119-170413-576819.jsonl` confirms both links, the 64x35
canvas and resumed image frames with replies from both panels.

## Exact-model menu follow-up

Tracing `ChooseActivity.showMenuType` resolves another model distinction:
internal app type **3**, selected by our `0x83`, branches at `0416` to `17a8`
and selects `clzs_bt_ble_16`. The following replacement checks require customer
`0001` with certain product IDs; our customer `0007` does not match them.
`ChooseActivity.<clinit>` constructs this selected navigation list with:

1. Text
2. Gallery
3. Program/channel list
4. DIY still images
5. DIY animation
6. Remote control
7. Widescreen music visualization
8. Clock
9. Combined image/text
10. Settings

The selected list does **not** include `ScoreboardActivity`, `CountDownActivity`
or `SecondChronographActivity`, although other model lists contain these
activities. Selected instruction excerpts are retained in
`.research/panel-capabilities/target-menu-evidence.txt`; full method dumps
preserve the register constants and branch context.

This is evidence that these native numerical tools are not exposed by the
normal Android 3.7.9 model-specific navigation path. It is consistent with the
held tests, but does not prove the firmware lacks every possible implementation
or entry sequence. The next bounded native candidate should come from the
selected menu, such as clock mode, rather than assume generic APK commands
apply equally to this product. Menu exposure itself is not hardware validation.

## Clock style 1: verified native execution

`ColockActivity.bindData` maps app display type 3 to `arrResidTime_16`, an
eight-entry style list. Selecting an item sends its zero-based index plus one.
The first time-format argument is `mIsTime12`: `BaseSend.sendColockMode`
inverts it into packet byte 5, so wire 1 selects 24-hour format. Byte 6 is
the show-date flag. Date fields are year minus 2000, month, day and weekday
Monday=1 through Sunday=7. Selected evidence is retained in
`.research/panel-capabilities/clock-model-evidence.txt` and the full class dumps.

`.research/clock_observation.py` checked the pinned upstream builder against
the explicit Europe/Berlin date, synchronized time, uploaded the known RGB TEST
baseline, then sent `0b 00 06 01 01 01 00 1a 0b 13 04` (style 1, 24-hour,
date hidden, 2026-11-19 Thursday). The panel returned `05 00 06 01 01`.
Capture: `captures/clock-observation-20261119T160724Z.jsonl`.

The owner observed a green clock with a blinking colon, an animated character
described tentatively as a duck, and **minutes changing after the script had
disconnected Bluetooth**. This verifies native clock rendering and autonomous
time progression for this style on the top panel, MCU 14.02 / Bluetooth 7.04.
The host sent no subsequent clock frames or time updates during that interval.
Colon blink rate, exact accuracy, all other styles, date display, long-term
drift and retention across loss of power remain unmeasured. A blinking colon
alone is not proof of second accuracy.

## Camera/game payload correction from static evidence

`PongFragment.onGameFrame(Bitmap)` and `CameraXActivity.sendAndRender`
compress bitmaps as **JPEG at quality 100**, read the resulting file bytes,
and pass them to `SendCore.sendCameraData`. That method selects data kind 0,
wire `00 00`, and splits content into windows of at most 12,288 bytes. Its
default payload builder uses a nine-byte header with no CRC for kind 0:

| Offset | Field |
| --- | --- |
| 0..1 | Current window bytes plus 9, little-endian |
| 2..3 | `00 00` |
| 4 | Default flag 0 |
| 5..8 | App `ledFrameSize`, little-endian; 4096 in the traced type-3 configuration |
| 9 onward | JPEG content for the window |

`ChooseActivity.setLedType` starts with frame size 4096 and does not replace it
in the `0x83` branch. `ByteUtils.int2byte` confirms the integer byte order.
Evidence excerpts: `.research/panel-capabilities/jpeg-frame-evidence.txt` and
`frame-length-byte-order.txt`; full `SendCore.payload`, `payload$default`,
`shouldCrc` and `sendCameraData` dumps preserve the framing logic.

The historical RGB888 reference instead sent 3,072 pixel bytes with frame-size
field 3072. Its failed rendering does not determine JPEG support. This finding
identifies a new candidate codec; it does not establish throughput, color
quality, frame rate or compatibility. The normal menu selected for our model
also omits the camera/game activities, so generic APK code alone is insufficient
to assert this panel supports JPEG frames.

### Bounded JPEG rendering result

`.research/jpeg_observation.py` generated a 64x16 baseline JPEG, quality 100,
containing red, green, blue and white blocks with JPEG text. The 1,607-byte
file was wrapped in one 1,616-byte packet, header `50 06 00 00 00 00 10 00 00`,
and sent in seven acknowledged GATT writes. JPEG SHA-256:
`c9cafb11eba55620276cf1816098af82631b1ad27f732cc69b37213f6e034811`.
The panel sent `05 00 00 00 01` after the last write. Capture:
`captures/jpeg-observation-20261119T161033Z.jsonl`. The previous owner-confirmed
native clock was the visual baseline; no image or clock updates followed the
JPEG transfer.

The owner reported **"the default LED bootimage"**, not the JPEG diagnostic.
Thus this packet sequence elicited a reply but did not establish correct JPEG
rendering. The status byte is retained without assigning it an undocumented
success meaning. No throughput or decoder support claim follows from it.

The post-connection `ChooseActivity$bindListener$1` callback was also checked:
its frame-size override to 12,288 applies when the MCU selector equals 2;
that does not match the tested MCU major 14. The traced type-3 frame-size value
therefore remains 4096 in this path. Decoder compatibility, another model's
initialization, JPEG encoder details and other entry requirements remain open.

## Game-focused investigation candidates

For interactive games, the remaining questions concern small live updates,
presentation timing, latency and scaling. Native GIF restart is verified for
cached sequences; it does not establish arbitrary sprite positioning, seek,
layer compositing or firmware-side game logic.

A further static trace recovered `DiyImageMoveType` values: no effect 0,
horizontal mirror 1, vertical mirror 2, whole-image movement 3, erase 4.
`LedView.undoDispatchTouch` constructs direction values and passes them through
`CPaintRunTimeItem` to the editor listener. `SendCore.sendDiyImageData` writes
the movement type into the native DIY packet's option field; for whole-image
movement it substitutes `arrMoveDirectionNum` for the usual color/coordinate
payload. Its other branches also assemble grouped same-color coordinates.
Evidence: `.research/panel-capabilities/diy-movement-evidence.txt`, plus the
inventoried `SendCore.sendDiyImageData` method. These are actual builder paths,
not verified hardware scroll, blit, copy-region or sprite operations.

Game-oriented investigation priorities, with the first follow-up results below:

1. Sparse/grouped pixel changes and native movement: update a few objects or
   shift a scrolling scene without uploading an entire image. Establish mode
   entry, preservation of existing pixels, clipping/wrapping and erase behavior
   first; previous fast-pixel and PNG-overlay tests failed.
2. Actual input-to-display latency and cross-panel onset: measure a moving
   object crossing the seam. Separate display behavior from GATT/ACK timing,
   and compare one panel versus two under realistic game frames.
3. Presentation control: search for a supported receive-then-present or buffer
   swap operation that could prevent half-old/half-new wall frames. No such
   general live-frame command is verified; cached-GIF restart does not prove it.
4. Transport and scheduling: controlled PNG size/chunk/ACK experiments and
   bounded frame-rate sweeps with freshness recorded. The wall's 10-fps limit
   is software policy, not a measured hardware ceiling. The current sender
   uploads both panels concurrently, then waits for both replies before the
   next canvas version. Earlier unsafe pipelining/fast-write failures remain
   negative evidence, not permission to assume a faster mode works.
5. Cached-media limits and scale: establish selection/reuse of multiple native
   sequences, overlay preservation and longer alignment stability; then test
   additional panels when available. Only two simultaneous physical panels
   have been verified. Cached loops already suit predetermined sequences;
   dynamic interaction still needs a proven live-update path.

## Bounded DIY drawing and image-operation results

The APK's `DiyImageFun` enum distinguishes four `04 01` mode values:
0 `QUIT_NOSAVE_KEEP_PREV`, 1 `ENTER_CLEAR_CUR_SHOW`,
2 `QUIT_STILL_CUR_SHOW`, and 3 `ENTER_NO_CLEAR_CUR_SHOW`.
Actual editor callers use mode 1 for initial entry and mode 3 for a re-edit
branch. These names describe app intent; they do not establish preservation of
an independently uploaded PNG. Evidence is retained in
`.research/panel-capabilities/diy-mode-evidence.txt` and `diy-mode-callers.txt`.

Two held, owner-observed experiments used `.research/diy_operations_observation.py`
on the top panel. Every native command used an acknowledged GATT write; painting,
movement and mirror commands produced no application-level reply. The mode-entry
reply was `0500040101`. No save or clear-all operation was sent.

1. A completed RGB PNG upload contained BASE text, a blue border and a yellow corner mark.
   The test then entered mode 3 (`0500040103`) and painted a red 4x4 square
   at source coordinates x=48..51, y=5..8 with one 40-byte grouped command.
   The owner saw **only a red square**. The sequence did not preserve the PNG
   background; observation did not isolate whether mode entry or painting hid it.
   A subsequent horizontal-mirror command left the square on the right.
   Capture: `captures/diy-observation-20261119T163344Z.jsonl`.
2. To remove PNG/native mixing from the experiment, mode 1 was followed by a
   complete native baseline: black background, red square at source x=8..11,
   and green at x=40..43, both y=5..8. The 33 grouped commands covered all
   1,024 coordinates exactly once, totaled 2,312 bytes, and were each at most
   72 bytes. Offline reconstruction exactly matched the source. The owner
   confirmed red on the left and green on the right.
   Whole-image right movement by 8 used `090005010300000008`; the owner reported
   no movement. Their accompanying approximate positions differed from the
   source, so this is not a measured coordinate mapping. Horizontal mirror
   `0a000501010000000000` then left red on the left and green on the right.
   Capture: `captures/diy-observation-20261119T163759Z.jsonl`.

These results verify static native grouped drawing but establish neither working
whole-image movement nor horizontal mirroring in the tested sequences. They do
not prove that every parameter, entry state or firmware variant lacks those
operations. Vertical mirror, erase and native-to-native incremental preservation
remain separate questions. Full-frame RGB PNG streaming remains the verified
live game path; cached GIF restart remains useful for predetermined sequences.
Both diagnostic sessions exited without saving and restored the shared ring demo.

## Two-panel acknowledged-chunk comparison

The wall worker already requested 500-byte acknowledged chunks at this checkpoint.
`.research/wall_chunk_benchmark.py` compared 244 and 500 on the same open links,
using 57 identical ring-source frames per block on the saved 64x35 layout
(three hidden rows). Both panels uploaded concurrently; each canvas waited for
both strict PNG completion replies before the next. No FPS pacing, pipelining
or write-without-response mode was used. Block order was 244, 500, 500, 244.

| Block | Chunk bytes | Completed canvases/s | Median wall completion ms | Median top / bottom ms | Top / bottom GATT writes |
| --- | --- | --- | --- | --- | --- |
| 1 | 244 | 5.180 | 194.976 | 194.919 / 79.732 | 67 / 69 |
| 2 | 500 | 5.047 | 195.050 | 195.000 / 79.565 | 57 / 57 |
| 3 | 500 | 4.994 | 195.124 | 195.072 / 79.613 | 57 / 57 |
| 4 | 244 | 4.623 | 210.157 | 210.104 / 94.321 | 67 / 69 |

All 228 combined frames (456 panel uploads) completed with `0500020003`.
Larger chunks reduced writes but did not establish a consistent wall-throughput
improvement: the first three median completion times were essentially unchanged,
and both panels were slower in the final block. The top panel governed the
barrier in this run. Connection scheduling and panel processing are candidates
for further investigation; these timings do not isolate either cause.

Capture: `captures/wall-chunk-benchmark-20261119T164536Z.jsonl`; private summary:
`.research/panel-capabilities/wall-chunk-benchmark-summary.json`.
These are host completion measurements under these connection conditions,
not physical LED latency, a firmware FPS ceiling, or a replacement for earlier
faster runs. No application transport change followed from this comparison.
The controller was restored and resumed combined ring uploads in
`captures/wall-ui-20261119-174629-484442.jsonl`.

## Resident playback and mixed-region follow-up

The [program/region report](archive/PROGRAM_REGIONS_TESTS.md) traces the program
list declaration, the separate six-byte business button command, custom remote
serial allocation starting at 111, and the native template container. On the
top panel, button 1 triggered scrolling text without an upload. Button 2 also
triggered scrolling, but the owner did not confirm different content. Native
text/image preview instead showed the default LED image. These findings do not
yet establish arbitrary stored-animation switching or independent region updates.
The report preserves exact packets, observation limits, candidate codec assignment
and private capture references.

## Inventory artifacts and reproducibility

Input identity and hashes are documented in [firmware metadata](firmware-metadata.md).
The script `.research/map_panel_capabilities.py` parsed 2,514 app/game class
definitions from the reference APK. Most are generated/callback/UI classes;
that number is not a capability count. `SendCore` has 147 methods including
generated helpers, defaults and wrappers, likewise not 147 hardware functions.

Ignored `.research/panel-capabilities/` retains:

- `class-inventory.json`: class/field/method inventory, literals, central calls
  and selector checks.
- `feature-callers.json`: 393 UI methods with direct calls to inventoried
  central classes; this is not a complete interprocedural call graph.
- `disassembly-index.json` and `disassembly/`: exact class-name mapping to
  case-safe hash filenames and selected static instruction dumps.
- `extraction-summary.txt`: extraction counts and central method names.

Re-run from the repository root:

```powershell
.\.tools\apk-inspect\Scripts\python.exe -X utf8 .research/map_panel_capabilities.py
```

The analysis does not execute Android code, install the APK, contact vendor
servers or connect to Bluetooth. App commands and phone features above were
identified from method bodies/callers; unresolved functionality remains marked
as such instead of being inferred from labels alone.

## How to use this map before choosing an implementation

1. Finish resolving model checks and dormant/current paths for any candidate
   family. Preserve packet format, supported parameters and response patterns.
2. Test one function family at a time on a single panel with visual confirmation,
   then disconnected observation where autonomy matters. An upload ACK alone
   does not establish the display behavior.
3. Add persistence, timing, capacity and two-panel observations as separate
   evidence. Keep generic SDK features separate from exact-panel observations.
4. Choose the playback/control architecture from those results. The current
   survey does not select native GIFs, faster streaming or replacement firmware
   as the route in advance.
