# Local pypixelcolor patch

`pypixelcolor-public-chunk-size.patch` adds an optional `chunk_size` keyword to
both public clients. It applies to commit
`c8cbaebca6df7797a7bcface8a1c4ca33e499973` of
[pypixelcolor](https://github.com/lucagoc/pypixelcolor).

The working checkout is `.research/ipixel-chunk-size`, branch
`feat/public-chunk-size`. The original `.research/ipixel` checkout and the app's
pinned dependency remain unchanged. Published as
[pypixelcolor PR #90](https://github.com/lucagoc/pypixelcolor/pull/90) on
2026-11-16, from `TakalNL:feat/public-chunk-size`, commit
`cfbc7bd0cb392bb499ee35c8cc9dce40cd2c8893`.

```python
async with AsyncClient(address, chunk_size=500) as client:
    await client.send_image_hex(png.hex(), '.png', save_slot=0)
```

`None` retains each command's existing default, normally 244 bytes. Explicit
values must be integers from 1 through 512. Acknowledged writes remain enabled
by default; writes without response additionally respect the characteristic's
advertised limit. Selecting 500 bytes is an opt-in setting for verified hardware,
not a proposed change to the default. Connection settings, ACK handling and
pacing are unchanged.

The patch contains implementation, public type signatures, generator templates,
documentation and 28 regression cases. All 68 upstream tests pass:

```powershell
Set-Location .research\ipixel-chunk-size
& ..\..\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

The cache provider is disabled because writing pytest's cache in this local
checkout hangs under the workspace filesystem restrictions. The new stub
constructor signatures match the generator. Other generated annotations already
differ in the pinned baseline under Python 3.13; this patch preserves those
existing annotations rather than changing unrelated signatures.

To apply to a separate clean checkout at the pinned commit:

```powershell
git apply --check "/path/to/led-wall/patches/pypixelcolor-public-chunk-size.patch"
git apply "/path/to/led-wall/patches/pypixelcolor-public-chunk-size.patch"
```

To run the app's Starfall benchmark against this checkout without installing it:

```powershell
$env:PYTHONPATH = "$PWD\.research\ipixel-chunk-size\src"
.\.venv\Scripts\python.exe examples\public_game_stream.py $deviceId --chunk-size 500 --seconds 120 --output captures\public-chunk500-new.jsonl
Remove-Item Env:PYTHONPATH
```

Omit `--chunk-size` for the unchanged default. Use a new output filename for
each run. Only non-saving slot 0 is used. The benchmark records the import path
and explicit option so patched-client results cannot be confused with the
unmodified upstream or app adapter. See
[STARFALL_STREAM_TESTS.md](STARFALL_STREAM_TESTS.md) for hardware evidence.

## Hardware result and proposed upstream scope

On the verified Windows/64x16 panel, two 120-second Starfall runs through the
same patched `AsyncClient` completed 1,175/1,200 updates with defaults and
1,200/1,200 with `chunk_size=500`. P95 API time was 112.602 ms versus 90.951 ms.
Every completed upload had its strict final reply, both sessions disconnected,
and the owner confirmed correct rendering with little visible difference.
The source images and all other client settings were identical. This is one
sequential pair on one host/panel; it does not establish broad hardware support.
The app's 168 tests also pass against both original and patched imports.

Suggested PR title: **Expose optional chunk_size on Client and AsyncClient**.

The concrete problem is that users of the public API cannot select larger
acknowledged chunks even when their hardware supports them. Small framed images
just over 244 bytes then need an additional acknowledged write. The change lets
applications opt in through the supported constructor while retaining existing
defaults. It can be reviewed independently of our app and its transport adapter.

Keep command-result error propagation, failed-connect cleanup and unknown-device
handling in separate proposals. They are not part of this patch. The focused
code proposal is now PR #90; the separate hardware compatibility report remains
an unpublished draft.

## Pre-submission validation — 2026-11-16

All local checks passed; no code changes were needed during this round.

| Check | Result |
| --- | --- |
| Upstream blocking flake8 command (`--select=E9,F63,F7`) | Passed, zero findings |
| Upstream advisory flake8 command | 409 findings, identical to the unmodified pinned baseline; none added |
| Library tests in a fresh environment | 68 passed |
| App tests with original library | 168 passed |
| App tests with patched source | 168 passed |
| Source distribution and wheel built from that distribution | Both built successfully |
| All library tests against the installed built wheel, outside the source checkout | 68 passed |
| Public stub constructor signatures versus generator templates | Match; both stub outputs parse |
| Exported patch versus checkout | Exact match, including new test file |
| Patch application to clean pinned source (`git apply --check`) | Passed |
| Original app dependency checkout | Clean and still active by default |

The isolated check environment is `.tools/upstream-pr-check`; it does not modify
the app's `.venv`. It uses Windows, CPython 3.13.9, flake8 7.5.0, pytest 9.2.0,
Bleak 3.1.0, Pillow 13.0.0 and Hatchling 1.33.0. Library tests used the existing
cache-provider workaround described above. The advisory comparison matches
diagnostic path/message/count while ignoring line-number shifts.

Build command, run from the workspace root:

```powershell
.\.tools\upstream-pr-check\Scripts\python.exe -m build .research\ipixel-chunk-size --no-isolation --outdir .tools\upstream-pr-dist
```

Local build artifacts are in `.tools/upstream-pr-dist`. Lint logs and installed
wheel test output are in `.tools/upstream-pr-results`; both directories are
ignored. The wheel test used copies of the library's tests and a separate pytest
configuration without the checkout's `pythonpath=src`, and verified that the
import came from the isolated environment's `site-packages`.

These are local Windows checks, not a completed GitHub Actions run. Upstream's
CI uses Ubuntu with Python 3.13 and still needs to run on a submitted PR. The
previous successful hardware comparison was not repeated in this software-only
validation round. Publication followed this validation round.

## Publication

At the recorded submission checkpoint, the PR was open and ready for review.
Its title, revised description,
six-file list and head commit were verified against the approved local preview.
The description explains the benchmark as small 64x16 PNG images from a scrolling
game and includes the AI-assistance disclosure. Exact submission text is in
[submitted description](../../patches/PR_BODY.md). The approved file hashes and
publication JSON records are retained privately.

GitHub's [Python application workflow](https://github.com/lucagoc/pypixelcolor/actions/runs/43885508470)
was awaiting approval from an upstream maintainer at that checkpoint, with no
CI jobs run. This was an approval requirement, not a failed test result.
These are dated observations, not a claim about the PR's current status.
