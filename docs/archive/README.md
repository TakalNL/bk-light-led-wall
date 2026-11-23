# Research archive

These reports describe historical code, commands and test conditions. Start with
[current validation](../validation.md) for the present supported behaviour.
Internal briefs, obsolete entry points, cleanup diaries and publication JSON
records are preserved privately rather than included in the public source.

| Topic | Reports |
| --- | --- |
| Reference implementations | [Source research](RESEARCH.md) |
| Investigation timeline | [Preserved checkpoints and follow-ups](INVESTIGATION_CHECKPOINTS.md) |
| First contact and protocol | [Hardware](HARDWARE_TESTS.md), [protocol](PROTOCOL.md), [range](RANGE_TESTS.md) |
| Images, GIFs and endurance | [Animation](ANIMATION_TESTS.md), [GIF](GIF_TESTS.md), [library tests](LIBRARY_PANEL_TESTS.md) |
| External test artwork | [Provenance](ART_SOURCES.md), [eyes benchmark](EYES_BENCHMARK.md) |
| Public client and contribution | [Lifecycle](PUBLIC_CLIENT_TESTS.md), [streaming](STARFALL_STREAM_TESTS.md), [patch validation](UPSTREAM_PATCH.md) |
| Fast transport and negative probes | [Fast mode](FAST_MODE_TESTS.md), [grouped pixels](GROUPED_PIXELS_TESTS.md), [PNG pipeline](PNG_PIPELINE_TESTS.md) |
| Windows tuning and integration | [Connection](WINDOWS_CONNECTION_TESTS.md), [timing](WINDOWS_TRANSPORT_PACING_TESTS.md), [app profiles/reconnect](GAME_STREAMING_PROFILE_TESTS.md) |
| Resident playback and region commands | [Program and mixed-region observations](PROGRAM_REGIONS_TESTS.md) |

Original capture filenames are retained inside ignored private archives, not
committed as public data. Recovery is described in [development](../development.md#private-archives).
Old command snippets may use `examples/`; current runners are indexed in
[tools](../../tools/README.md). Application settings now live under `.state/`.
Some later experiments used private scripts under `.research/`. Those scripts,
downloaded APKs and raw captures are not shipped, so their historical commands
cannot be reproduced from this repository alone. Public diagnostic/experiment
runners remain available under `tools/`. Owner-specific addresses have been
redacted from public reports; original captures remain private.

The [posted PR #88 comment](upstream/PR88_COMMENT.md) retains its observation
and public link. The chunk-size patch and submitted description remain under
[patches](../../patches/README.md). Publication status in dated reports describes
the recorded checkpoint; it is not a live upstream status check.
