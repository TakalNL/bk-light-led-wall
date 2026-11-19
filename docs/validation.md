# Validation checkpoint

Hardware observations below are from the owner's Windows host and 64x16 panels.
Protocol checks and owner visual observations are recorded separately.

| Check | Result |
| --- | --- |
| Game output, Standard | Established acknowledged 10-fps path |
| Windows profile, two live-worker trials | 11.983 and 11.992 completed uploads/s |
| Interactive Windows-profile Starfall | Owner confirmed correct gameplay and reconnect |
| Saved-address reconnect, two worker checks | Ready in 1.561 and 2.912 s; previously about 16 s |
| Reopened real UI after discovery change | Ready in 1.562 s; owner accepted the result |
| Public-client chunk-size comparison | 1,175/1,200 default versus 1,200/1,200 with 500-byte chunks |
| Two-panel stacked wall, 2026-11-19 | Both type 0x83 / 64×16; 96 combined frames acknowledged |
| Wall completion time, same run | Mean 71.5 ms; maximum 118.767 ms; last 66.9 ms |
| Physical order | Owner confirmed cyan panel 1 above orange panel 2 |

The source suite passes **288 tests**, with four optional upstream-branch
cases skipped. This includes settings and recording checks. Hidden desktop
checks confirmed all three games load the shared settings directly. Earlier
cleanup checks also covered profile selection, start/pause and disconnect.
At that cleanup checkpoint, a 46,072-byte wheel passed UI,
rendering and PNG-encoding checks from an independent environment outside the
source directory; developer tools were absent from that installation. This is
a packaging smoke check, not the still-outstanding clean-machine test.
Run the current suite using the command in [development](development.md).

The two-panel diagnostic used a shared 64×32 canvas and a 10-fps Standard target.
Its private capture is `captures/wall-20261119-130810-956161.jsonl`, with a matching
identify PNG. Both links were held simultaneously and each canvas version waited
for both image completion replies. Owner confirmation establishes physical order;
moving-image seam quality and physical refresh synchronization remain unmeasured.
Hidden Tk checks covered the wall's layout presets, reversal, rotation, demo,
full-canvas Snake, image fitting and media relayout. Synthetic checks cover exact
pixel crops, all mounting rotations, GIF timing/transparency, slow-panel frame
coordination, invalid replies, idle disconnection, setup failures, duplicate
physical devices and cancellation cleanup.

A follow-up run on the final device-metadata path completed another 30 shared
frames (`captures/wall-20261119-131648-022411.jsonl`). The visible desktop
controller then connected both panels in 6.95 seconds and completed 197 combined
frames without errors at the inspection checkpoint. It was left streaming the
seam demo. This verifies the UI-to-worker path as well as the diagnostic runner.

Variable compensation checks cover 0, 2, 3 and 32 pixels in both axes, exact
omission of hidden image rows/columns, black preview gaps, rotation/origin
preservation, settings round trips and invalid values. A slow-panel test changes
the image and gap while an upload is pending, verifying that the next frame
uses its matching layout. Live changes cannot replace connected device
identities. Hidden Tk checks exercised the gap controls while marked connected,
including preserving demo playback and saving/reloading the positions.

The live compensation check (`captures/wall-compensation-20261119-133011-114374.jsonl`)
kept both links open while switching from 0 to 2 to 3 pixels: 28, 26 and 28
combined frames were acknowledged respectively. The updated controller was then
reopened at 3 pixels (64×35 virtual canvas); its first inspection found 130
completed shared frames and no errors. The ring was left running for owner
assessment of the compensated seam.

The game-focused capability follow-up verified a fully native grouped-pixel
baseline, but mode-3 PNG preservation, horizontal mirroring and rightward
movement were not demonstrated in the owner-observed sequences. A two-panel
244/500/500/244-byte acknowledged-chunk comparison completed all 228 combined
frames (456 PNG uploads), at 4.623-5.180 completed canvases/s under those connection
conditions. Fewer GATT writes did not establish a consistent speed improvement.
See the [capability map](panel-capabilities.md#two-panel-acknowledged-chunk-comparison)
for conditions and the distinction between host completion and physical timing.

## Evidence index

- [Game profile integration and reconnect](archive/GAME_STREAMING_PROFILE_TESTS.md).
- [Windows connection preference](archive/WINDOWS_CONNECTION_TESTS.md).
- [Fast-write and timer comparisons](archive/WINDOWS_TRANSPORT_PACING_TESTS.md).
- [Public-client streaming and chunk-size comparison](archive/STARFALL_STREAM_TESTS.md).
- [Public-client lifecycle, PNG and GIF](archive/PUBLIC_CLIENT_TESTS.md).
- [Protocol evidence ledger](archive/PROTOCOL.md).
- [Library, GIF capacity and endurance checks](archive/LIBRARY_PANEL_TESTS.md).
- [Grouped-pixel findings](archive/GROUPED_PIXELS_TESTS.md).
- [Negative pipeline experiment](archive/PNG_PIPELINE_TESTS.md).
- [Resident playback trigger and mixed-region investigation](archive/PROGRAM_REGIONS_TESTS.md).

Historical reports retain their original test conditions and counts. Do not
combine measurements across different hosts, profiles or workloads as a single
benchmark. Twelve fps is a scheduled upload target, not a physical refresh claim.

Raw captures, downloaded artwork and local reference checkouts are private.
Completed material is compressed with file hashes under `archive/private/`;
see [recovery instructions](development.md#private-archives).
