# Public pypixelcolor client trial — 2026-11-16

**Result: the unmodified public `AsyncClient` passed the basic connection,
reconnection, PNG upload and GIF upload/playback trial on the owner's panel.**
The owner confirmed both images looked correct and the GIF kept looping after
disconnect. The application backend has not been changed by this trial.

## Tested configuration

- Upstream commit: `c8cbaebca6df7797a7bcface8a1c4ca33e499973`, version 0.5.0.
  The imported upstream source checkout was checked for modifications; none were
  present under `src/pypixelcolor`.
- Same Windows host, CPython 3.13.9, Bleak 3.1.0 and known B.K. Light 3226274 unit
  as the earlier experiments. The public API returned type `0x83`, 64×16,
  MCU version string `14.02` and secondary version string `7.04`.
- `AsyncClient(address)` with constructor defaults: acknowledged writes, no
  project transport adapter, forced GATT cache settings, service filters,
  chunk-size overrides, added pacing or monkeypatches.
- Executed on the normal Windows host because prior sandbox attempts could
  discover the panel but could not open its BLE connection.
- The public client automatically queries information/firmware during connect
  and synchronizes the panel's time-of-day to host local time. The public cached
  `get_device_info()` getter returned the same information object.

## Results

| Operation | Result |
| --- | --- |
| First public connect | Passed in 1.836 s |
| Disconnect | Passed in 0.135 s |
| Reconnect the same client instance | Passed in 4.634 s; same profile/versions |
| Disconnect after reconnect | Passed in 0.148 s |
| Fresh public client in a second process | Connected in 1.513 s |
| Original `LIB` RGB PNG, 289-byte input, slot 0 | Public call returned in 88.587 ms; debug log contains `0500020003`; owner confirmed rendering |
| Original twenty-frame numbered GIF, 4,088-byte input, slot 0 | Public call returned in 910.274 ms; debug log contains `0500030003`; owner confirmed numbered playback and looping |
| Disconnect after uploads | Passed in 0.157 s; followed by twelve seconds with no connection or application writes |

The PNG was held for eight seconds before the GIF upload. Its input SHA256 was
`9ec87422e73be39269fcd76db61e2a5971b17d5d2c44f328f8db9279f8601bf5`.
The GIF input SHA256 was
`0f6a6f290870d70e89555be1fcd56a00c9a0676be429211b046746306c6183a2`.
Both are the original project diagnostics from the preceding backend cleanup.
The GIF has twenty 200-ms frames and a four-second encoded loop. The public
image API automatically supplies cached device information and may re-encode
GIFs; these hashes identify the input files, not a captured outgoing wire stream.

Both uploads used non-saving slot 0. The saved slot-1 startup GIF was not
overwritten. No reset, clear, delete, persistent upload or firmware-update command was
sent. No further hardware tests are running; the numbered GIF is left playing.

## Reproduction and evidence

The standalone runner is [../../tools/diagnostics/public_client_test.py](../../tools/diagnostics/public_client_test.py).
Use an explicitly identified panel and original native-size PNG/GIF inputs:

```powershell
.\.venv\Scripts\python.exe examples\public_client_test.py $deviceId --mode connect --reconnect --output captures\public-connect-new.jsonl
.\.venv\Scripts\python.exe examples\public_client_test.py $deviceId --mode content --png captures\cleanup-static-host-20261116.png --gif captures\cleanup-gif-host-20261116.gif --output captures\public-content-new.jsonl
```

Private evidence is in `captures/public-client-connect-20261116.jsonl` and
`captures/public-client-content-20261116.jsonl`, plus their `.debug.log` sidecars.
The sidecars contain upstream/Bleak debug messages and can include unique device
identifiers; they are not sanitized publication artifacts.

## What this establishes

The custom Windows connection settings were unnecessary for these successful
trials under the current conditions. This does not identify the cause of the
earlier connection failures. The host already had Windows device/GATT state;
this was not a second-host, second-unit or clean-cache test.

A subsequent [Starfall streaming comparison](STARFALL_STREAM_TESTS.md) completed
1,175 of 1,200 scheduled updates through the public API in 120 seconds (9.78 fps),
versus all 1,200 through the current adapter at 10 fps. The owner confirmed both
looked correct, with little visible difference. The game backend remains on the
adapter, which had more timing headroom in this paired trial.

Large/multi-window public uploads, unavailable-device and mid-transfer failure
recovery, other games, and the synchronous `Client` wrapper remain untested
through the public API. Physical timing was not instrumented.

The existing 164 hardware-free tests also passed after adding the standalone
runner and updating the compatibility documentation.
