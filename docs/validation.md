# Validation checkpoint

Hardware observations below are from the owner's Windows host and 64x16 panel.
Protocol checks and owner visual observations are recorded separately.

| Check | Result |
| --- | --- |
| Game output, Standard | Established acknowledged 10-fps path |
| Windows profile, two live-worker trials | 11.983 and 11.992 completed uploads/s |
| Interactive Windows-profile Starfall | Owner confirmed correct gameplay and reconnect |
| Saved-address reconnect, two worker checks | Ready in 1.561 and 2.912 s; previously about 16 s |
| Reopened real UI after discovery change | Ready in 1.562 s; owner accepted the result |
| Public-client chunk-size comparison | 1,175/1,200 default versus 1,200/1,200 with 500-byte chunks |

The cleaned source suite passes **246 tests**, with four optional upstream-branch
cases skipped. This includes settings-migration and recording checks. Hidden
desktop checks passed for all three games, including profile selection,
migration, start/pause and disconnect. A 46,072-byte wheel also passed UI,
rendering and PNG-encoding checks from an independent environment outside the
source directory; developer tools were absent from that installation. This is
a packaging smoke check, not the still-outstanding clean-machine test.
Run the current suite using the command in [development](development.md).

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

Historical reports retain their original test conditions and counts. Do not
combine measurements across different hosts, profiles or workloads as a single
benchmark. Twelve fps is a scheduled upload target, not a physical refresh claim.

Raw captures, downloaded artwork and local reference checkouts are private.
Completed material is compressed with file hashes under `archive/private/`;
see [recovery instructions](development.md#private-archives).
