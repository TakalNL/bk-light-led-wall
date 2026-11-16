# Submitted pypixelcolor contribution

[PR #90: Expose optional chunk_size on Client and AsyncClient](https://github.com/lucagoc/pypixelcolor/pull/90)
adds opt-in chunk sizing while preserving defaults and acknowledged writes.

- Base: `c8cbaebca6df7797a7bcface8a1c4ca33e499973`.
- Submitted head: `cfbc7bd0cb392bb499ee35c8cc9dce40cd2c8893`.
- Local checkout: `.research/ipixel-chunk-size`, branch `feat/public-chunk-size`.
- [Patch](pypixelcolor-public-chunk-size.patch) and [submitted description](PR_BODY.md).

The app still uses the original pinned dependency. Do not apply the patch to its
active checkout merely to run games; the adapter already selects its own chunk
size. Keep the PR checkout while the contribution is being maintained.

To check the patch against a separate clean checkout at the base commit:

```powershell
git apply --check D:/repos/led-screen/patches/pypixelcolor-public-chunk-size.patch
```

The patch had 68 passing upstream tests, package/stub/lint checks and a direct
public-client hardware comparison. Full details are in the
[archived validation](../docs/archive/UPSTREAM_PATCH.md) and
[streaming report](../docs/archive/STARFALL_STREAM_TESTS.md).
Completed preview/publication metadata and the posted PR #88 feedback are
retained in [the upstream archive](../docs/archive/upstream/).
