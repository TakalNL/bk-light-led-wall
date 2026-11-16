# Product direction: an app for buyers of this panel

Updated 2026-11-16. The intended outcome is
an application people buying this exact device can install and use. The original
research brief remains unchanged in `project.md`; this file records the current
product direction alongside the experimental evidence.

## Current checkpoint

Snake, Starfall and Micromaze are working Windows source prototypes on the
owner's verified panel. They share the pypixelcolor-backed transport and one
desktop shell. Standard remains 10 fps; the optional Windows profile targets
12 fps with negotiated connection preferences and automatic Standard fallback.
Real-worker checks measured 11.983 and 11.992 uploads/second. The owner confirmed
manual gameplay and reconnect worked. Saved-address discovery now stops on the
matching advertisement: two full worker connections became ready in 1.561 and
2.912 seconds, compared with about 16 seconds previously. The reopened UI was
ready in 1.562 seconds, and the owner accepted the result. See
[app integration evidence](GAME_STREAMING_PROFILE_TESTS.md).

The latest full suite passed 242 tests, with four optional upstream-branch cases
skipped. The chunk-size contribution is published as
[pypixelcolor PR #90](https://github.com/lucagoc/pypixelcolor/pull/90); hardware
feedback was also posted on PR #88. The wider compatibility report remains a
local draft. The application workspace still has no root Git repository or
packaged end-user release. A versioned app checkpoint, distributable Windows
build and clean installation on a second host are the next practical milestones.

## Playable prototype available

The local Snake desktop prototype is implemented; see [Snake instructions](games/snake/README.md) and
`games/snake/Start Snake.cmd`. It provides keyboard controls, a PC preview, score, pause,
restart and optional live output to the verified panel. The game defaults to five
moves per second, with acknowledged RGB uploads capped at ten per second and
one image in flight. The latest unsent board replaces older states.

Rules and controls were checked locally, the current unit acknowledged the
initial ready board, and the owner subsequently confirmed Snake worked.
Starfall is the second playable prototype: a side-scrolling shooter with three
enemy types, enemy fire, two collectible upgrades, three lives, per-life result
screens and a final carrier boss. It shares the desktop shell and acknowledged
RGB transport, with separate rules and renderer; see [Starfall instructions](games/starfall/README.md).
The owner confirmed Starfall works. Micromaze adds an enemy-free first-person
maze and exit, also confirmed working by the owner; see
[Micromaze instructions](games/micromaze/README.md). Each prototype now has its
own directory under `games/`, with shared UI and transport in `games/common/`.
These source prototypes are not packaged general releases; installation,
second-host/unit and licensing work below still applies.

## Intended users and initial support

People buying the Action B.K. Light panel, article 3226274. The tested unit's
label includes `37/2026`, its reported app is iPixel Color, and its verified grid
is 64×16. One tested unit is evidence of compatibility with that unit, not a
guarantee every production batch has identical firmware or internals.

Recommended first platform: Windows, because all hardware testing so far used
Windows. This is a recommendation, not a settled cross-platform requirement.
The distributed application should not require installing Python, editing a
MAC address in source, or issuing terminal commands.

## First useful release

1. Find nearby candidate panels, let the user select one, then verify the FA
   service layout and known dimensions before any content upload. Treat unknown
   device types as unsupported rather than defaulting to 64×16.
2. Offer a visual identify pattern so a user can confirm the selected physical
   panel when multiple similar devices are nearby.
3. Open a PNG/GIF, preview it at 64×16, offer clear fit/crop choices and preserve
   GIF timing. Display content size and validation failures in ordinary language.
4. Upload with progress, bounded timeouts and useful connection errors. Local
   GIF playback continues after disconnect; avoid ongoing streaming for loops.
5. Remember the user's selected panel locally and reconnect for the next upload.
   Recover cleanly from failures; never blindly repeat partial transfers.
6. Ship a small original or clearly licensed example animation and dependency
   notices. The downloaded eyes art has no stated redistribution license and is
   private test material, not an app-bundled asset.

Brightness, hardware orientation, persistent slots, firmware updates and multi-
panel synchronization are outside this first release until their operations are
validated on the supported unit(s).

## Reuse and upstream work

The application now depends on pinned `pypixelcolor`. All games and hardware
experiments use its command builders, ACK manager and send loop through one
instrumented connection adapter. The earlier parallel PNG/GIF framing and
experimental send loop have been removed. Our adapter retains Windows settings,
timeouts, strict reply/profile checks and capture logging. A direct trial of the
unmodified public `AsyncClient` has now passed connect/reconnect and visually
confirmed PNG/GIF playback; see [PUBLIC_CLIENT_TESTS.md](PUBLIC_CLIENT_TESTS.md).
A paired Starfall streaming trial then completed 1,175/1,200 updates through the
default public API versus 1,200/1,200 through the adapter over two minutes; both
looked correct to the owner. A focused [local library patch](patches/README.md)
then exposed optional public `chunk_size` configuration. With the same patched
client and connection defaults, default chunks completed 1,175/1,200 updates and
500-byte chunks completed 1,200/1,200, both owner-confirmed correct. Retain the
game adapter's lifecycle bounds and diagnostics until public-client integration;
see [STARFALL_STREAM_TESTS.md](STARFALL_STREAM_TESTS.md). Larger public uploads
and failure recovery remain untested. Evaluate redistribution contents before
publishing a packaged release.

A subsequent [fast-mode PNG comparison](FAST_MODE_TESTS.md) passed a fully
watched two-minute 10-fps run. Requested 15-fps runs averaged roughly 11 fps with
both write modes, and the owner reported brief pauses/missing frames in both.
Acknowledged game writes remain the default. This experiment does not establish
a useful fast-mode gain or resolve fast GIF/pixel failures. The subsequent
optional 12-fps Windows profile uses connection preferences and fixed deadlines,
without fast writes or timer-resolution changes; its validation is above.

Keep application UI, asset preparation, connection UX, device profiles and
packaging separate from the protocol backend. Keep the experiment tools as
diagnostics and regression evidence. Avoid maintaining parallel protocol code
without a concrete compatibility or application need.

Primary upstream report: a concise, qualified compatibility report to
`lucagoc/pypixelcolor`. Secondary: model/label compatibility information for
`Pupariaa/Bk-Light-AppBypass`. No findings from the FA panel currently establish
anything new for the unrelated FFF1/FFD1 protocol repositories. A raw-RGB failure
report to the Web Bluetooth reference would need careful reproduction and state
description before being presented as a library defect.

See `UPSTREAM_REPORT.md` for a local draft. No report has been posted.

## Release evidence needed

- A fresh installation test on a second Windows machine, without our development
  tools, virtual environment, prior GATT cache or stored device address.
- At least one other purchaser's unit, recording model label, information type,
  version bytes and confirmed operations, with unique identifiers kept private.
- Repeated discovery/connect/upload/disconnect cycles, power-cycle recovery and
  handling of unavailable/busy devices. The cache workaround must be evaluated
  under good RF conditions before being made a default.
- Distributable packaging, clear versioning, dependency/asset notices and an
  intentional license for our own application code. No application license has
  been chosen yet.
- A reproducible report export containing relevant model/version/error data
  without unrelated nearby-device advertisements or unique device identifiers.

Describe support as tested profiles and verified operations. Encoded 50 fps is
not an instrumented physical refresh specification, and 528 frames / 244,687 bytes
is a successful test file rather than a measured hardware maximum.
