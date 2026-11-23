# Resident playback and mixed-region investigation

Dates: 2026-11-19 and follow-up 2026-11-22. Top panel only: `<TOP_BLE_ADDRESS>`, type `0x83`,
64x16, MCU/Bluetooth version reply `080005800e020704`. These are bounded
observations, not a firmware dump or an exhaustive command survey.

## App paths recovered

`ChannelListActivity.SendChannel` constructs a program-list packet:
two-byte length, wire opcode `08 80`, selected-item count, a zero byte, then
one-byte serial numbers. It queues the selected media for upload afterward.
For MCU major greater than 4, `sendDevice1$lambda$10` sends that packet; its
`onResult` callback starts the upload queue after a five-byte reply ending in 1.
Thus the app uses this as upload preparation/list declaration. A response alone
does not establish selection of already stored content.

`BusinessRemoteControlActivity.initList$lambda$4` has a separate button path:
`06 00 07 80 <one-based-button> <language>`. The activity derives language
from whether the saved language contains `zh`: 1 for that branch, 0 otherwise.
It sends the six-byte packet through both app transports without media data.
`BusinessControlModel.autoSendChannel$lambda$32` assigns custom remote content
serials starting at 111 and declares them through `08 80` before uploading.
The mapping between those serials and the six-byte button command is not yet
verified on hardware. Button counts or serial ranges in this code are not
measured firmware capacities.

`SendCore.sendTemplateData` builds actual region records rather than flattening
this particular path into a full-frame GIF. Each record has a 16-byte descriptor:
four-byte little-endian data length, data-kind byte, x, y, width, height, and
seven border/effect/reserved bytes, followed by that region's data. The type-2
template puts text on the right and an image on the left. `sendDataTemInner`
uses internal data kind 7 (wire `04 00`), a CRC-bearing 15-byte upload header,
and replaces header byte 13 with the region count. In its preview branch it
sets byte 14 to 101 (`0x65`). This is a whole-template upload path; no separate
command for replacing one resident region was established here.

This native template mechanism and the app's other text/image or GIF generation
paths must be distinguished. Generic builder code does not establish support
on this particular panel profile.

## Held hardware observations

`.research/program_regions_observation.py` first uploads a known RGB PNG
containing BASE within a cyan border. It holds each command's result until the
owner responds. All writes use GATT write-with-response; no new saved-media
upload, deletion or clear-all command is requested.

| Test | Packet / reply | Owner observation and limit |
| --- | --- | --- |
| Declare existing program 1 | `07000880010001`; reply `0500088001` | BASE stayed visible. No standalone playback transition demonstrated. Presence and contents of current program 1 were not read back. |
| Business button 1, language 0 | `060007800100`; no application reply within two seconds | Scrolling text starting with "I'm in a hurry", then two other texts in different colors, then the LED boot image. Resident playback triggered without a media upload. Factory origin versus prior app installation is unresolved. |
| Two-region preview | 289-byte packet, header `2101040000120100004b3dc9fe0265`; no application reply within two seconds | Default LED image. Correct mixed-region rendering not established. |
| Business button 2, language 0, separate connection | `060007800200`; no application reply within two seconds | Owner thought it might be the same sequence, observed scrolling text ending with "high beam", and had not watched closely. No distinct button-to-content mapping established. |

The region fixture contains 134 bytes of pinned-upstream native text data for
green REGION at x=16, y=0, width=48, height=16, followed by a 108-byte RGB PNG
at x=0, y=0, width=16, height=16. The PNG contains a yellow L and red border.
Text descriptor kind is 3, matching the builder. Image descriptor kind 1 is a
candidate PNG assignment; the app's image-kind assignment was not fully traced.
Geometry follows template type 2. Header fields, record lengths, two-region
consumption and CRC were checked offline, but these checks do not validate
firmware codec support or the required entry sequence. SHA-256 of the complete
packet: `7c2b0636a228604611869505492d6e587fd4d3e9383f47fa0d725a302438b72c`.

The first capture is `captures/program-regions-observation-20261119T183642Z.jsonl`;
button 2 is in `captures/program-regions-observation-20261119T184054Z.jsonl`.
Each session sent exit-mode on completion and restored the wall controller.
The owner-confirmed resident sequence establishes a useful small playback
trigger. It does not yet establish arbitrary cached-animation selection,
independent region updates, shared playback timing or custom-content bank reuse.

## Retained static evidence

Ignored `.research/panel-capabilities/program-regions/` contains extracted
methods with instruction offsets, including:

- `ChannelListActivity-SendChannel.txt` and `ChannelListActivity_sendDevice1_1_1-extra.txt`.
- `BusinessRemoteControlActivity-initList_lambda_4.txt`, the activity constructor
  in `BusinessRemoteControlActivity-extra.txt`, and `BusinessControlModel-extra.txt`.
- `SendCore-sendTemplateData.txt`, `SendCore-sendDataTemInner.txt`,
  `SendCore-payloadTemChannel.txt`, and `SubzoneListActivity-extra.txt`.
- `region-preview.bin`, `region-preview.json`, the fixture PNGs, and
  `owner-observations.json` with capture references and the owner's wording.

The research helper has a `--prepare-only` option for regenerating and checking
the region fixture without connecting to Bluetooth. No production application
transport or playback behavior was changed in this investigation.

## Cached A/B follow-up, 22 November 2026

The next bounded experiment follows the app's actual custom-remote upload chain:
`BusinessControlModel.sendGifData` calls `SendCore.sendChannelGifData`, whose
default mask makes `sendDataInner` use the normal saving path rather than the
`0x65` preview override. `payloadChannel` takes the supplied serial byte for
the business activity. For a single-window GIF, the reconstructed message
matches pinned upstream `send_image(..., save_slot=serial)` byte for byte.

`.research/cached_switch_observation.py` prepares original two-frame 64x16 GIFs
with 600-ms frame durations and infinite looping. A has a cyan left bar and
large A0/A1 label; B has a magenta right bar and B0/B1 label. Pillow decoding
was checked against every source pixel and duration before upload.

| Fixture | GIF bytes | SHA-256 |
| --- | --- | --- |
| A | 395 | `71a46be93a6763f0637839ea8d7debb085d7f17d6473f9e6470050a5223b312e` |
| B | 385 | `ab7a453434e077d5a4b5fa1f7c7b1e9c957d3d7bf554c115f48f2e51937235c7` |

The helper's writable targets are limited to the top panel, custom banks
111/112, or ordinary slots 1/2. It uses acknowledged writes, strict normal GIF
completion replies, held observation states and no clear/delete commands.
Saving these fixtures replaces prior content in the addressed banks.

### Custom banks 111/112

Capture: `captures/cached-switch-observation-20261122T190608Z.jsonl`.
Declaration `0800088002006f70` returned `0500088001`. Following the app's
declaration/settle/upload order, A and B each returned `0500030003`; the owner
separately confirmed correct A0/A1 and B0/B1 looping immediately after upload.

| Follow-up from a neutral HOLD PNG | Packet / reply | Owner observation |
| --- | --- | --- |
| Business button 1 | `060007800100`; no application reply in two seconds | Scrolling preset text or default image, not A. |
| Short A header retaining bank 111 | `0f000300008b010000d48f1445026f`; `0500030000` | HOLD remained. This differs from the earlier successful `0x65` restart reply. |
| Program-list / upstream show-slot packet for 111 | `0700088001006f`; `0500088001` | HOLD remained. |

These observations verify immediate rendering of custom-bank uploads, but not
later retrieval or persistence of those banks. An intervening PNG changes the
display state, so this sequence alone does not settle direct GIF-to-GIF recall
or whether the earlier restart mechanism retains anything beyond its current
GIF context.

### Ordinary slots 1/2, with a neutral PNG

Capture: `captures/cached-switch-observation-20261122T191121Z.jsonl`.
The identical GIF payloads were sent to slots 1/2 after declaring
`0800088002000102`. Both GIFs again returned strict completion. The sender
then uploaded HOLD and sent `07000880010001`, independently checked against
the installed upstream `show_slot(1)` builder. The panel replied `0500088001`,
but the owner still saw HOLD. This is not evidence of successful saved-content
selection. The helper subsequently sent exit-mode and disconnected.
The owner then confirmed HOLD remained after that exit/disconnect sequence.

### Direct GIF-to-GIF recall: verified

The intervening PNG was removed from the experiment. In
`captures/cached-switch-observation-20261122T191738Z.jsonl`, the helper declared
ordinary slots 1/2 and uploaded the same A/B files, then sent only selection
commands while native GIF playback was active. All three returned `0500088001`:

| Action after initial A/B uploads | Application bytes | Owner observation |
| --- | --- | --- |
| Select slot 1 while B was playing | `07000880010001` | Cyan A0/A1. |
| Select slot 2 | `07000880010002` | Magenta B0/B1; the owner was told no intermediate image had been sent. |
| Select slot 1 again | `07000880010001` | Cyan A0/A1 again. |

No PNG, GIF payload or short GIF header was sent between these selections.
The three selections totaled 21 application bytes; this excludes BLE framing
and replies. The earlier negative PNG-to-GIF results remain valid for those
sequences, but do not establish inability to select stored content. The tested
display context matters; its exact firmware state semantics remain unresolved.

### Recall after reconnect: verified

After the direct A/B/A session exited and disconnected, a new connection
queried identity/version and sent `07000880010002`. It uploaded no media and
did not redeclare or populate the slots. The reply was `0500088001`, and the
owner confirmed magenta B0/B1. Capture:
`captures/cached-switch-observation-20261122T192203Z.jsonl`. The final helper
disconnected without an exit-mode command, leaving the selected native display
in place. The file contains only three GATT writes: identity/time query,
version query and the seven-byte selection command.

This establishes at least two user-provided GIFs selectable without re-upload,
including across a Bluetooth reconnect, on this top panel. This sequence did not
establish two-file power-cycle retention (verified later below), maximum slot
count, selection latency, behavior after arbitrary other modes, or the mapping
of custom remote banks 111/112.
The earlier single-file slot-1 power-cycle result is separate evidence.

For games, cached selection can supply predetermined scenes, reactions or
transitions using very little control traffic. It does not supply arbitrary
live sprite positioning, region updates, or atomic multi-panel presentation.

Private static methods, fixture hashes, raw captures and owner wording are
retained under `.research/panel-capabilities/cached-switching/`. No production
application behavior was changed for these experiments.

### Two-file power-cycle retention: verified during the controls survey

During the later 22 November native-controls test, the top was left in
orientation1 / brightness10 and disconnected. With no phone-app interaction,
the owner removed USB power for about five seconds, restored power, and reported:
"Intro animation plays upside down, after that A01, upside down, after that
switches to B0 upside down, then cycles back and forth between those two".
No A/B payloads or selectors were sent during this observation. The controls
survey uploaded only the temporary GO preview, without replacing saved slots.

This establishes retention of both original ordinary-slot A/B GIFs through that
power cycle and automatic playlist playback. Per-slot selection after power
loss was not separately exercised. It does not establish larger storage
capacity or custom-bank behavior. Capture:
`captures/native-controls-observation-20261122T200518Z.jsonl`; verbatim owner
reports: `.research/panel-capabilities/native-controls-owner-observations.json`.
The [controls validation report](../validation.md#native-display-controls-follow-up-2026-11-22)
records the surrounding commands and power-cycle conditions.
