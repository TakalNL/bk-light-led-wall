The public clients currently use the chunk size chosen by each command builder, normally 244 bytes. Applications with hardware that supports larger acknowledged writes cannot select that size through the public API. A small framed image just over 244 bytes therefore needs an additional acknowledged write.

This adds an optional `chunk_size` keyword to `Client` and `AsyncClient`, forwarded through `DeviceSession`:

```python
from pypixelcolor import AsyncClient

async with AsyncClient(address, chunk_size=500) as device:
    await device.send_image("./image.png")
```

`None` preserves each command's existing chunk size. Explicit values must be integers from 1 through 512; booleans are rejected. For writes without response, the selected size is additionally capped at the connected characteristic's advertised maximum. Acknowledged writes remain the default.

The patch updates documentation, public type stubs and their generator, and makes synchronous-client cleanup safe when constructor validation raises. It adds 28 regression cases covering both public clients, payload integrity, default preservation, invalid options and characteristic limits.

### Validation

- All 68 library tests passed on Windows with CPython 3.13.9 and Bleak 3.1.0.
- All 68 tests also passed against the built wheel installed into an isolated environment, outside the source checkout.
- The CI blocking flake8 command passed with zero findings; advisory findings were unchanged from the baseline.
- The source distribution and a wheel built from that distribution both built successfully.
- Public stub constructor signatures match the generator templates.

### Hardware observation

Two sequential 120-second runs sent the same sequence of 1,200 small PNG images from a scrolling game at a scheduled 10 images per second through the patched public `AsyncClient`. The images were native 64x16 RGB, with framed payloads of 157–322 bytes: some required two 244-byte writes, while all fit in one 500-byte write. The chunk-size option was the only changed client setting; both runs used acknowledged writes and upstream connection defaults.

| Metric | Default chunks (244 bytes) | `chunk_size=500` |
| --- | ---: | ---: |
| Completed scheduled uploads | 1,175 / 1,200 | 1,200 / 1,200 |
| Skipped source states | 25 | 0 |
| Upload/API time, p95 | 112.602 ms | 90.951 ms |

Each completed upload received its expected final reply, and both sessions disconnected cleanly. The hardware owner confirmed correct rendering with little visible difference. The sender selected the latest source state when late, so skipped states represent scheduling overruns, not measured dropped LED frames.

This was one sequential pair on a B.K. Light 64x16 panel with Windows, Bleak 3.1.0 and a reported MTU of 517. It does not establish broader hardware/platform support or justify changing the default. Larger sizes remain an opt-in choice for verified devices and backends. Ubuntu CI remains to run on this PR.

AI assistance was used for the implementation, tests and this description. Display output was visually checked by the hardware owner.
