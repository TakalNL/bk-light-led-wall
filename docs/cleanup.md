# Cleanup record — 2026-11-16

## Source and documentation

- Created the initial local Git checkpoint `0f177dd` before modifying files.
- Reduced the root from 21 Markdown files to one 79-line README (previously 378).
- Added concise architecture, compatibility, validation, development and roadmap
  guides. Full historical reports remain under `docs/archive/`.
- Preserved the original project brief without content edits and retained PR
  previews/publication metadata in the archive. The active patch and submitted
  description remain under `patches/`.
- Moved diagnostic runners to `tools/diagnostics/` and retained research runners
  and fixtures under `tools/experiments/`. Removed two redundant CLI wrappers.
- Kept experimental regressions under `tests/experiments/`; no tests were dropped.
- Extracted shared game startup, bitmap fonts and recording utilities. Runtime
  game imports no longer depend on experimental modules.
- Migrated panel preferences into ignored `.state/panel-settings.json`. Games
  now record summaries by default; full packet tracing is explicit.

## Local material

| Verified private archive | Files | Original | ZIP |
| --- | ---: | ---: | ---: |
| Captures | 650 | 91.94 MiB | 26.14 MiB |
| Unused reference checkouts | 508 | 44.41 MiB | 36.13 MiB |
| Prior validation/build evidence | 137 | 3.22 MiB | 2.82 MiB |

Archives are under `archive/private/` with per-file SHA-256 manifests. ZIP contents,
archive hashes and source hashes were checked before unpacked originals were
removed. Downloaded artwork remains private. The active Python, `.venv`,
`.research/ipixel` dependency and `.research/ipixel-chunk-size` PR checkout remain.

Discarded rebuildable downloads, cache entries, build copies and the disposable
validation environment. Permission-protected generated wheel copies and residual
UV-cache files were preserved under `archive/private/protected-generated/` instead
of changing permissions. An empty protected `.pytest_cache` directory remains.
Those generated exceptions are not research evidence and are not in the verified
ZIP manifests. The reviewed directory totals indicate approximately 187 MiB less
disk use, including the archives and preserved exceptions.

## Verification

- Full suite after cleanup: **246 passed, 4 optional cases skipped**.
- Source desktop checks: all three games passed migration, profile and controls.
- Installed-wheel checks outside the source directory: all three games opened,
  rendered and encoded RGB PNGs without the developer tools package.
- Wheel contents exclude the moved experiment modules; build size 46,072 bytes.
- Local Markdown links were checked; the unchanged original brief is exempt
  because its original references are historical.
- Active interpreter/dependency imports and migrated settings were verified.

No changes were published remotely, and no new panel streaming experiment was
needed for this cleanup. Historical hardware measurements remain qualified by
their original reports; the cleanup does not establish additional compatibility.
