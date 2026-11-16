# PNG range and connection reliability

Date: 2026-11-14. Target: the previously identified B.K. Light panel; verified
64×16 and successful PNG/CRC upload at the earlier PC-side position.

## Two-metre desk test

The owner moved the powered panel to a desk approximately **2 metres from the
PC** and confirmed it was lit and using a **separate USB supply**. The earlier
successful PNG test used PC USB power. Position and supply therefore both changed;
this is a test of the new configuration, not an isolated distance comparison.
Wall/floor obstructions and exact controller/antenna orientation were not reported.

Three independent attempts used the verified PNG format, Windows cached metadata
for the known FA service, a 15-second scan, a 30-second connection timeout, and
the same source-derived information/version exchanges before image upload.
Distinct labels FAR1/FAR2/FAR3 were prepared so an old image could not count as
proof of a new upload. No automatic partial-frame retries were enabled.

| Trial | Advertisement RSSI | Result | Elapsed | Application writes |
| --- | --- | --- | --- | --- |
| FAR1 | Target not detected | 15-second scan found no target; connection not attempted | 15.107 s | 0 |
| FAR2 | -101 dBm, last scan advertisement | Connection/setup timed out after 30 seconds | 45.139 s including scan | 0 |
| FAR3 | -101 dBm, last scan advertisement | Connection/setup timed out after 30 seconds | 45.122 s including scan | 0 |

**Outcome: 0/3 end-to-end PNG trials completed.** No information query, version
query or PNG bytes were written in any trial. No visual rendering confirmation
is requested for these failed attempts. The prepared previews are not delivered
images. RSSI is a discovery snapshot, not a connected/live signal measurement.

Private evidence:

- `captures/range-2m-far1-20261114.jsonl`
- `captures/range-2m-far2-20261114.jsonl`
- `captures/range-2m-far3-20261114.jsonl`

The cache workaround that enabled the earlier PNG upload was insufficient in
this configuration. These failures occurred before the PNG protocol could be
tested at distance, so they do not contradict the earlier successful PNG format.
The cause is not established: distance, position/orientation, host radio behavior,
and the changed power arrangement have not been isolated.

## Antenna retest at the same desk

The owner deferred the proposed near-PC/same-supply comparison and reported
installing the PC antennas, requesting another test at the current desk location.
The panel remained at the reported approximately two-metre placement on its
separate USB supply. Three new connections used the same cached-service option,
scan/connection timeouts, PNG protocol and write pacing as FAR1–FAR3. Labels
ANT1/ANT2/ANT3 distinguished these images from previous display contents.

| Trial | Last advertisement RSSI | Connection/setup after scan | Frame / chunks | PNG writes | Expected reply |
| --- | --- | --- | --- | --- | --- |
| ANT1 | -67 dBm | 0.762 s | 433 bytes / 2 | 89.6 ms | `0500020003` |
| ANT2 | -69 dBm | 0.871 s | 514 bytes / 3 | 119.6 ms | `0500020003` |
| ANT3 | -74 dBm | 0.731 s | 517 bytes / 3 | 119.6 ms | `0500020003` |

**Outcome: 3/3 uploads completed with the expected reply.** After the last
experiment finished and disconnected, the owner confirmed: “Yes, ANT3 and the
pattern look correct.” This independently confirms the final image rendered;
ANT1 and ANT2 were acknowledged but not separately confirmed visually.
Each trial started with a fixed approximately 15-second discovery scan, excluded
from the connection/setup column. PNG write timing spans the first chunk attempt
to the last chunk completion; reply arrival was 134–149 ms from the first chunk.
Different label compression accounts for the differing frame sizes. No retries
were needed. The complete transmitted bytes were checked against each preview's
PNG/CRC frame offline.

Private evidence:

- `captures/range-2m-ant1-20261114.jsonl` (18:05:43–18:06:00 UTC)
- `captures/range-2m-ant2-20261114.jsonl` (18:06:15–18:06:32 UTC)
- `captures/range-2m-ant3-20261114.jsonl` (18:09:04–18:09:21 UTC)
- `captures/range-2m-antennas-20261114-observation.md`

The much stronger discovery readings and three successful fresh connections
strongly support antenna reception as a major factor in the earlier failures.
This short retest establishes working PNG upload at the reported desk placement,
not long-term reliability or maximum range. RSSI remains a scan snapshot.
Cached metadata was enabled before and after the antenna change, so this does
not establish whether fresh Windows GATT enumeration now works. The near-PC
comparison was not performed, and the separate supply itself has not been
measured; it supported all three successful trials.

## Tooling

`examples/static_image.py --label FAR1` generates a distinct PNG label (1–5 ASCII
letters/digits/spaces). Captures now include scan start, target resolution and
the last Windows advertisement RSSI before connection, even when setup fails.
Image encoding, chunk limits, response matching and timeout settings remain the
same as the successful PNG path. Instrumentation verification: 86 automated
tests passed; none of those tests use physical Bluetooth hardware.
