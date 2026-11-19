# Research archive

These reports describe historical code, commands and test conditions. Start with
[current validation](../validation.md) for the present supported behaviour.
The original source layout and full documents are recoverable from Git checkpoint
`0f177dd`. The [original brief](project.md) is preserved without content changes.

| Topic | Reports |
| --- | --- |
| Original requirements and source reviews | [Brief](project.md), [research](RESEARCH.md), [old README](ROOT_README.md), [old product plan](PRODUCT_PLAN.md) |
| First contact and protocol | [Hardware](HARDWARE_TESTS.md), [protocol](PROTOCOL.md), [range](RANGE_TESTS.md) |
| Images, GIFs and endurance | [Animation](ANIMATION_TESTS.md), [GIF](GIF_TESTS.md), [library tests](LIBRARY_PANEL_TESTS.md) |
| External test artwork | [Provenance](ART_SOURCES.md), [eyes benchmark](EYES_BENCHMARK.md) |
| Public client and contribution | [Lifecycle](PUBLIC_CLIENT_TESTS.md), [streaming](STARFALL_STREAM_TESTS.md), [patch validation](UPSTREAM_PATCH.md), [unposted report draft](UPSTREAM_REPORT.md) |
| Fast transport and negative probes | [Fast mode](FAST_MODE_TESTS.md), [grouped pixels](GROUPED_PIXELS_TESTS.md), [PNG pipeline](PNG_PIPELINE_TESTS.md) |
| Windows tuning and integration | [Connection](WINDOWS_CONNECTION_TESTS.md), [timing](WINDOWS_TRANSPORT_PACING_TESTS.md), [app profiles/reconnect](GAME_STREAMING_PROFILE_TESTS.md) |
| Resident playback and region commands | [Program and mixed-region observations](PROGRAM_REGIONS_TESTS.md) |

Original capture filenames are retained inside ignored private archives, not
committed as public data. Recovery is described in [development](../development.md#private-archives).
Old command snippets may use `examples/`; current runners are indexed in
[tools](../../tools/README.md). Application settings now live under `.state/`.

The wider upstream hardware report is still a draft. Publication metadata and
the posted PR #88 comment are retained in `upstream/`; the active chunk-size
patch and submitted description remain under [patches](../../patches/README.md).
