# Resident playback and mixed-region investigation

Date: 2026-11-19. Top panel only: `95:53:D1:21:30:2F`, type `0x83`,
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
