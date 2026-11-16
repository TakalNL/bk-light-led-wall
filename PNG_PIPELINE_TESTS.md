# Bounded PNG pipeline experiment

The hypothesis is that a second complete PNG can be transferred while the host
waits for the previous image's completion reply. Earlier acknowledged complete
PNGs averaged roughly 11 uploads/second when requesting 15 fps. Native grouped
pixels were slower, and concatenating native commands in one write drew only
the first colour in the static probe. Neither approach replaced the app's
acknowledged 10-fps transport.

## Isolated implementation

`examples/png_pipeline_stream.py` uses upstream `send_image_hex` builders and
`send_plan` for all image framing and GATT writes. It accepts only non-saving
slot-0 PNGs with one window fitting one negotiated write. A copied plan leaves
application reply waits to a separate FIFO ledger. Original upstream plans,
the installed library, public clients and production adapter are unchanged.

Depth one waits for a completion reply before submitting another image. Depth
two allows at most two reserved images awaiting replies. GATT writes remain
acknowledged and serialized in both modes; this is not fast transport and does
not run existing public-client uploads concurrently. When behind schedule,
the sender chooses the latest source state rather than queueing stale images.

The ledger reserves before writing, so a reply arriving before the OS write
call returns is retained. Every notification must be exactly `0500020003`.
Missing replies have a four-second deadline from reservation; unrelated replies
and replies arriving with no pending image stop the stream. After the final
drain, a 250-ms observation interval detects extra late replies. On error, the
connection closes before a single recovery attempt on a fresh connection with
a conventional acknowledged `STOP 0` PNG. No ambiguous image is retried.

**Replies contain no image identifiers.** FIFO attribution assumes normal
ordered one-reply-per-upload behaviour. A duplicate reply while another image
is pending cannot be distinguished from that image's genuine reply; a duplicate
could mask a missing reply. Matched counts and visual correctness are evidence,
not proof that every unique image was decoded or physically presented. Report
completion-reply throughput, not measured panel refresh rate.

## First comparison

The first comparison uses the same deterministic Starfall game source at
15 fps for 30 seconds, first depth one and then depth two. The ordinary game
simulation remains at 20 Hz with normal controls, collisions and lives. All
450 complete RGB source images fit in one 500-byte write (157-255 framed bytes).
The concatenated PNG input SHA256 is
`1dac1101534dae972bf9ac93ea40d141ae2ba6f2b0f4c1e747d4c7594e8d5560`.
Both modes use the unchanged installed upstream checkout
at `c8cbaebca6df7797a7bcface8a1c4ca33e499973`.
The END marker after each stream uses the conventional adapter with its normal
strict image completion check, after the ledger has drained and its notification
handler has been restored. No persistent slot, reset or clear command is used.

### Single-image control, 2026-11-16

The depth-one control submitted 333 images and received 333 exact completion
replies in 30.067 seconds: **11.075 completion replies/second**. It skipped 117
source states and never had more than one image awaiting completion. Reply time
was 89.898 ms median, 112.417 ms p95 and 135.018 ms maximum. GATT write time was
45.352 ms median and 67.820 ms p95. END 333 received the conventional strict
reply, and the connection closed cleanly. Private capture:
`captures/png-pipeline-depth1-15fps-30s-20261116.jsonl`.

### First depth-two attempt

The first two-image attempt stopped early under its strict notification rule.
The first image's write finished after 45.012 ms. The second started 71.601 ms
after stream start, before the first image's final reply. The first final reply
arrived after 89.799 ms, followed by `0500020000`. Two writes had completed, but
only one final reply had been counted when the unexpected status stopped the
stream. There is no sustained throughput result for this attempt.

Status 0 must not be counted as image completion. Upstream's ACK manager does
recognize status 0 as a window acknowledgement, so this early strict abort alone
does not establish that the second image could never finish. A separate bounded
two-image diagnostic was prepared to record this status while still requiring
two exact final replies within their original deadlines. It sends no third
image and never frees capacity for a status-0 response.

The first attempt closed its pipeline connection and recovered on a fresh
connection with a conventional acknowledged STOP 0 PNG, which received exactly
`0500020003`. The recovery then disconnected cleanly. Private capture:
`captures/png-pipeline-depth2-15fps-30s-20261116.jsonl`.

The first pair diagnostic did not establish overlap. Its first GATT write
completed after about 30 ms, but the scheduled second submission did not resume
before the first final reply at 74.637 ms. The diagnostic stopped before sending
the second image, explicitly recorded that no overlap was tested, and recovered
with an acknowledged STOP 0 PNG on a fresh connection. This is a scheduling
result, not evidence against firmware overlap support. Private capture:
`captures/png-pipeline-pair-probe-20261116.jsonl`.

A repeat removes the scheduled delay and submits the second image immediately
after the first GATT write returns, provided the first is still outstanding.
It still sends only two images, observes status 0 without completion credit,
and requires two exact final replies before an END marker.

### Immediate pair result: a final reply was missing

The immediate pair test genuinely overlapped two PNGs. The second reservation
occurred 29.915 ms after the first, while both were still awaiting replies.
One exact final reply arrived 75.046 ms after the first reservation. Status
`0500020000` followed with one image still pending; it was recorded without
releasing capacity or extending any deadline. No second final completion
arrived within four seconds of the second reservation, so the diagnostic
timed out with two submissions, one final reply and one outstanding image.
Private capture: `captures/png-pipeline-pair-probe-immediate-20261116.jsonl`.

The runner closed that connection and uploaded a conventional STOP 0 PNG on a
fresh connection. The recovery received exactly `0500020003` and disconnected
cleanly. The recovery marker has not been separately visually confirmed.

The depth-two pipeline did not pass completion verification on this setup.
Do not credit status 0 as success or claim a sustained pipeline FPS. Its exact
firmware meaning remains unresolved, and untagged final replies do not identify
which unique image completed. These results do not establish a universal panel
FPS ceiling or rule out every possible overlap timing. They do establish that
this bounded implementation cannot replace the verified sequential transport.
Keep the app's existing acknowledged 10-fps default. No hardware test remains
running; the last acknowledged image was STOP 0. Nothing from this round has
been posted upstream.

## Verification

Sixteen focused tests cover unchanged upstream payloads and original ACK
policies, rejection of saved/multi-window/oversized plans, separate accounting
for replies received together, unexpected and extra replies, missing and late
replies, replies before write completion, bounded capacity, serialized writes,
latest-state skipping, notification-handler restoration and write failure
without retry. Additional diagnostic checks ensure status 0 never counts as a
completion or extends a deadline, and a hung write respects the oldest pending
image's deadline. The simulated two-image case completes the target schedule;
that does not establish firmware pipeline support.
The sixteen-test pipeline suite passes after the diagnostic and deadline-handling
additions. The final full suite with the unchanged installed dependency passes
192 tests; four optional tests for the separate upstream grouped-pixel checkout
are skipped.

## Reproduction

Use fresh capture paths, confirm visual correctness before extending a run or
increasing the rate, and inspect `error`/`recovery_*` records before interpreting
an END marker. With the unchanged installed dependency:

```powershell
.\.venv\Scripts\python.exe examples\png_pipeline_stream.py $deviceId --depth 1 --fps 15 --seconds 30 --output captures\png-depth1-new.jsonl
.\.venv\Scripts\python.exe examples\png_pipeline_stream.py $deviceId --depth 2 --fps 15 --seconds 30 --output captures\png-depth2-new.jsonl
# Bounded two-image diagnostic; status 0 is observed but never counted as completion:
.\.venv\Scripts\python.exe examples\png_pipeline_stream.py $deviceId --depth 2 --pair-probe --output captures\png-pair-new.jsonl
```

Private captures include packet data and device information and remain ignored
by version control. No findings from this experiment have been posted upstream.
